/* Rogue Swarm, tier 1: Hull Breach.
 *
 * Galaga-style point-defense game rigged to be unwinnable: the ship launches
 * with 3 hull points, and every curtain volley spans the full screen with gaps
 * narrower than the ship, so each one is a guaranteed hit. Clearing all 80
 * drones takes far longer than 3 hits allow. The intended way through is an
 * exact-value memory scan for the hull counter and a write.
 *
 * raylib 6.2 with the rlsw CPU renderer over RGFW/X11, so it needs no GPU
 * (libGL is linked but never called). Logic steps at a fixed 60 Hz; drawing runs at 30 FPS by default.
 */
#include <raylib.h>
#include <dlfcn.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shard.h"
#include "ct.h"

#define W 480
#define H 640
#define SHIP_Y (H - 56)
#define SHIP_HW 14
#define SHIP_HH 9
#define START_HULL 3
#define INVULN_FRAMES 60
#define FIRE_COOLDOWN 8
#define CURTAIN_PERIOD 150
#define CURTAIN_STEP 20
#define AIMED_PERIOD 40
#define DIVE_PERIOD 70
#define WAVE_TIMEOUT (18 * 60)
#define WAVE_GAP 90
#define MAX_PB 48
#define MAX_EB 640
#define NSTARS 60
#define SIM_HZ 60

/* The HUD reads hull straight from here, so there is exactly one real copy. */
struct ship {
    int32_t hull;
    int32_t invuln;
    int32_t cooldown;
    float x;
};
static struct ship g_ship;

enum { D_DEAD, D_ENTER, D_FORM, D_DIVE, D_RETURN };
struct drone {
    float x, y, vx, vy;
    int state;
    int slot;
    uint32_t id;
};
struct bullet { float x, y, vx, vy; int live; };

enum { G_READY, G_PLAY, G_LOST, G_WON };

static struct drone drones[RS_DRONES];
static struct bullet pbul[MAX_PB], ebul[MAX_EB];
static float stars[NSTARS][2];
static int g_state, g_paused, g_frame, g_wave, g_wave_t, g_gap, g_kills;
static int g_curtain_t, g_aim_t, g_dive_t;
static uint8_t g_acc[16];
static char g_result[160];
static uint32_t rng_s = 0x2545f491u;

static int key_left, key_right, key_fire;

static uint32_t rnd(void)
{
    rng_s ^= rng_s << 13;
    rng_s ^= rng_s >> 17;
    rng_s ^= rng_s << 5;
    return rng_s;
}

static float slot_x(int slot) { return 62.0f + (slot % 8) * 51.0f + 28.0f * sinf(g_frame * 0.02f); }
static float slot_y(int slot) { return 72.0f + (slot / 8) * 40.0f; }

static void reset_run(void)
{
    memset(drones, 0, sizeof drones);
    memset(pbul, 0, sizeof pbul);
    memset(ebul, 0, sizeof ebul);
    sodium_memzero(g_acc, sizeof g_acc);
    g_ship.hull = START_HULL;
    g_ship.invuln = 0;
    g_ship.cooldown = 0;
    g_ship.x = W / 2.0f;
    g_wave = -1;
    g_wave_t = 0;
    g_gap = 30;
    g_kills = 0;
    g_curtain_t = CURTAIN_PERIOD;
    g_aim_t = AIMED_PERIOD;
    g_dive_t = DIVE_PERIOD;
    g_result[0] = 0;
}

static void spawn_wave(int w)
{
    for (int s = 0; s < RS_PER_WAVE; s++) {
        struct drone *d = &drones[w * RS_PER_WAVE + s];
        d->id = (uint32_t)(w * RS_PER_WAVE + s);
        d->slot = s;
        d->state = D_ENTER;
        d->x = slot_x(s);
        d->y = -24.0f - (s / 8) * 34.0f - (s % 8) * 6.0f;
    }
    g_wave = w;
    g_wave_t = 0;
}

static void enemy_shot(float x, float y, float vx, float vy)
{
    for (int i = 0; i < MAX_EB; i++)
        if (!ebul[i].live) {
            ebul[i] = (struct bullet){ x, y, vx, vy, 1 };
            return;
        }
}

static void open_command_link(void)
{
    uint8_t key[32], nonce[crypto_aead_chacha20poly1305_ietf_NPUBBYTES];
    unsigned char msg[sizeof rs_ct];
    unsigned long long mlen = 0;

    rs_key(g_acc, key);
    rs_nonce(nonce);
    if (crypto_aead_chacha20poly1305_ietf_decrypt(msg, &mlen, NULL, rs_ct, sizeof rs_ct,
                                                  NULL, 0, nonce, key) == 0 &&
        mlen < sizeof g_result - 1) {
        memcpy(g_result, msg, mlen);
        g_result[mlen] = 0;
        printf("COMMAND LINK KEY: %s\n", g_result);
    } else {
        snprintf(g_result, sizeof g_result, "COMMAND CODE CORRUPTED");
        printf("%s\n", g_result);
    }
    fflush(stdout);
    sodium_memzero(key, sizeof key);
    sodium_memzero(msg, sizeof msg);
}

/* The only place a drone dies, and the only place its shard is released. */
static void drone_destroyed(struct drone *d)
{
    uint8_t sh[16];
    rs_shard(d->id, sh);
    for (int i = 0; i < 16; i++)
        g_acc[i] ^= sh[i];
    sodium_memzero(sh, sizeof sh);
    d->state = D_DEAD;
    g_kills++;
}

static int ship_hit(float x, float y, float hw, float hh)
{
    return fabsf(x - g_ship.x) < SHIP_HW + hw && fabsf(y - SHIP_Y) < SHIP_HH + hh;
}

static void damage_ship(void)
{
    if (g_ship.invuln > 0)
        return;
    g_ship.hull -= 1;
    g_ship.invuln = INVULN_FRAMES;
}

static int wave_alive(void)
{
    int n = 0;
    if (g_wave < 0)
        return 0;
    for (int s = 0; s < RS_PER_WAVE; s++)
        n += drones[g_wave * RS_PER_WAVE + s].state != D_DEAD;
    return n;
}

static struct drone *random_drone(int state)
{
    int alive = wave_alive();
    if (!alive)
        return NULL;
    for (int tries = 0; tries < 32; tries++) {
        struct drone *d = &drones[g_wave * RS_PER_WAVE + (int)(rnd() % RS_PER_WAVE)];
        if (d->state == state)
            return d;
    }
    return NULL;
}

static void update(void)
{
    g_frame++;
    if (g_state != G_PLAY)
        return;

    /* ship */
    float speed = 4.5f;
    if (key_left)
        g_ship.x -= speed;
    if (key_right)
        g_ship.x += speed;
    if (g_ship.x < SHIP_HW)
        g_ship.x = SHIP_HW;
    if (g_ship.x > W - SHIP_HW)
        g_ship.x = W - SHIP_HW;
    if (g_ship.invuln > 0)
        g_ship.invuln--;
    if (g_ship.cooldown > 0)
        g_ship.cooldown--;
    if (key_fire && g_ship.cooldown == 0) {
        for (int i = 0; i < MAX_PB; i++)
            if (!pbul[i].live) {
                pbul[i] = (struct bullet){ g_ship.x, SHIP_Y - 12, 0, -9.0f, 1 };
                break;
            }
        g_ship.cooldown = FIRE_COOLDOWN;
    }

    /* waves */
    int alive = wave_alive();
    g_wave_t++;
    if (g_wave < RS_WAVES - 1 && (alive == 0 || g_wave_t > WAVE_TIMEOUT)) {
        if (alive == 0 && g_gap > 0)
            g_gap--;
        else {
            spawn_wave(g_wave + 1);
            g_gap = WAVE_GAP;
        }
    }

    /* drones */
    for (int i = 0; i <= g_wave && i < RS_WAVES; i++)
        for (int s = 0; s < RS_PER_WAVE; s++) {
            struct drone *d = &drones[i * RS_PER_WAVE + s];
            float tx = slot_x(d->slot), ty = slot_y(d->slot);
            switch (d->state) {
            case D_ENTER:
                d->x = tx;
                d->y += 3.0f;
                if (d->y >= ty)
                    d->state = D_FORM;
                break;
            case D_FORM:
                d->x = tx;
                d->y = ty;
                break;
            case D_DIVE:
                d->vx += (g_ship.x > d->x ? 0.06f : -0.06f);
                if (d->vx > 3.0f) d->vx = 3.0f;
                if (d->vx < -3.0f) d->vx = -3.0f;
                d->x += d->vx;
                d->y += d->vy;
                if (ship_hit(d->x, d->y, 10, 8))
                    damage_ship();
                if (d->y > H + 24) {
                    d->y = -24;
                    d->state = D_RETURN;
                }
                break;
            case D_RETURN: {
                float dx = tx - d->x, dy = ty - d->y, dist = sqrtf(dx * dx + dy * dy);
                if (dist < 4.0f)
                    d->state = D_FORM;
                else {
                    d->x += dx / dist * 4.0f;
                    d->y += dy / dist * 4.0f;
                }
                break;
            }
            default:
                break;
            }
        }

    if (wave_alive()) {
        if (--g_dive_t <= 0) {
            struct drone *d = random_drone(D_FORM);
            if (d) {
                d->state = D_DIVE;
                d->vx = 0;
                d->vy = 3.6f;
            }
            g_dive_t = DIVE_PERIOD;
        }
        if (--g_aim_t <= 0) {
            struct drone *d = random_drone(D_FORM);
            if (d) {
                float dx = g_ship.x - d->x, dy = SHIP_Y - d->y, n = sqrtf(dx * dx + dy * dy);
                enemy_shot(d->x, d->y + 8, dx / n * 3.6f, dy / n * 3.6f);
            }
            g_aim_t = AIMED_PERIOD;
        }
        /* Curtain volley: bullet gaps are narrower than the ship, so no
         * position on screen dodges it. One guaranteed hit per volley. */
        if (--g_curtain_t <= 0) {
            float phase = (float)(rnd() % CURTAIN_STEP);
            for (float x = phase; x < W; x += CURTAIN_STEP)
                enemy_shot(x, 120.0f, 0, 3.2f);
            g_curtain_t = CURTAIN_PERIOD;
        }
    }

    /* bullets */
    for (int i = 0; i < MAX_PB; i++) {
        struct bullet *b = &pbul[i];
        if (!b->live)
            continue;
        b->y += b->vy;
        if (b->y < -10) {
            b->live = 0;
            continue;
        }
        for (int k = 0; k < RS_DRONES; k++) {
            struct drone *d = &drones[k];
            if (d->state == D_DEAD || d->state == D_ENTER)
                continue;
            if (fabsf(b->x - d->x) < 13 && fabsf(b->y - d->y) < 11) {
                b->live = 0;
                drone_destroyed(d);
                break;
            }
        }
    }
    for (int i = 0; i < MAX_EB; i++) {
        struct bullet *b = &ebul[i];
        if (!b->live)
            continue;
        b->x += b->vx;
        b->y += b->vy;
        if (b->y > H + 10 || b->x < -10 || b->x > W + 10) {
            b->live = 0;
            continue;
        }
        if (ship_hit(b->x, b->y, 2, 4)) {
            b->live = 0;
            damage_ship();
        }
    }

    if (g_ship.hull <= 0) {
        g_state = G_LOST;
        return;
    }
    if (g_kills == RS_DRONES) {
        g_state = G_WON;
        open_command_link();
    }
}

/* ---- rendering (raylib) ---- */

static const Color C_CYAN = { 0, 230, 255, 255 };
static const Color C_RED = { 255, 69, 0, 255 };
static const Color C_MAG = { 255, 0, 255, 255 };
static const Color C_GOLD = { 255, 215, 0, 255 };
static const Color C_GREY = { 140, 140, 140, 255 };
static const Color C_GREEN = { 50, 205, 50, 255 };

static void text_c(int y, int size, Color col, const char *s)
{
    DrawText(s, W / 2 - MeasureText(s, size) / 2, y, size, col);
}

static void render(void)
{
    char line[96];

    BeginDrawing();
    ClearBackground(BLACK);
    for (int i = 0; i < NSTARS; i++)
        DrawPixel((int)stars[i][0], (int)stars[i][1], C_GREY);

    for (int k = 0; k < RS_DRONES; k++) {
        struct drone *d = &drones[k];
        if (d->state == D_DEAD)
            continue;
        Color c = d->state == D_DIVE ? C_RED : C_MAG;
        DrawTriangle((Vector2){ d->x - 11, d->y - 7 }, (Vector2){ d->x, d->y + 9 },
                     (Vector2){ d->x + 11, d->y - 7 }, c);
        DrawRectangle((int)d->x - 11, (int)d->y - 9, 22, 3, c);
    }

    for (int i = 0; i < MAX_PB; i++)
        if (pbul[i].live)
            DrawRectangle((int)pbul[i].x - 1, (int)pbul[i].y - 5, 3, 10, C_GOLD);
    for (int i = 0; i < MAX_EB; i++)
        if (ebul[i].live)
            DrawRectangle((int)ebul[i].x - 2, (int)ebul[i].y - 4, 4, 8, C_RED);

    if (g_state == G_PLAY && !(g_ship.invuln > 0 && (g_frame / 4) % 2))
        DrawTriangle((Vector2){ g_ship.x, SHIP_Y - SHIP_HH - 3 },
                     (Vector2){ g_ship.x - SHIP_HW, SHIP_Y + SHIP_HH },
                     (Vector2){ g_ship.x + SHIP_HW, SHIP_Y + SHIP_HH }, C_CYAN);

    snprintf(line, sizeof line, "HULL %d", g_ship.hull);
    DrawText(line, 10, 8, 20, g_ship.hull > 1 ? C_GREEN : C_RED);
    snprintf(line, sizeof line, "WAVE %d/%d", g_wave < 0 ? 0 : g_wave + 1, RS_WAVES);
    text_c(8, 20, RAYWHITE, line);
    snprintf(line, sizeof line, "DRONES %d", RS_DRONES - g_kills);
    DrawText(line, W - 10 - MeasureText(line, 20), 8, 20, RAYWHITE);

    switch (g_state) {
    case G_READY:
        text_c(240, 20, C_CYAN, "ROGUE SWARM // PD-1");
        text_c(280, 10, C_RED, "WARNING: HULL INTEGRITY 3 -- DRAINED BEFORE LAUNCH");
        text_c(305, 10, RAYWHITE, "80 hostile drones inbound. Shoot down every one.");
        text_c(355, 10, C_GREY, "ARROWS/A-D move   SPACE fire   P pause   R relaunch");
        text_c(390, 20, C_GOLD, "PRESS SPACE TO LAUNCH");
        break;
    case G_LOST:
        text_c(290, 20, C_RED, "HULL BREACH -- PD-1 LOST");
        text_c(325, 10, C_GREY, "PRESS R TO RELAUNCH");
        break;
    case G_WON:
        text_c(270, 20, C_GREEN, "SWARM DOWN. COMMAND LINK KEY:");
        text_c(305, 10, C_GOLD, g_result);
        break;
    }
    if (g_paused)
        text_c(210, 20, C_GOLD, "PAUSED");
    EndDrawing();
}

static void handle_input(void)
{
    key_left = IsKeyDown(KEY_LEFT) || IsKeyDown(KEY_A);
    key_right = IsKeyDown(KEY_RIGHT) || IsKeyDown(KEY_D);
    key_fire = IsKeyDown(KEY_SPACE);
    if (IsKeyPressed(KEY_SPACE) && g_state == G_READY)
        g_state = G_PLAY;
    if (IsKeyPressed(KEY_P) && g_state == G_PLAY)
        g_paused = !g_paused;
    if (IsKeyPressed(KEY_R) && g_state != G_PLAY) {
        reset_run();
        g_state = G_READY;
    }
}

/* Remote desktops (VNC/RDP) re-send the whole window on every present, so
 * drawing at 30 FPS halves their load. RS_FPS=15..60 overrides it. */
static int render_fps(void)
{
    const char *e = getenv("RS_FPS");
    int fps = e ? atoi(e) : 30;
    return fps < 15 ? 15 : fps > 60 ? 60 : fps;
}

/* raylib's RGFW backend dlopen()s these when it creates the window and
 * segfaults if one is missing, so check first and name the package. */
static int check_runtime_libs(void)
{
    static const char *libs[][2] = {
        { "libXcursor.so.1", "libxcursor1" },
        { "libXi.so.6", "libxi6" },
        { "libXext.so.6", "libxext6" },
    };
    int ok = 1;
    for (size_t i = 0; i < sizeof libs / sizeof libs[0]; i++) {
        void *h = dlopen(libs[i][0], RTLD_LAZY);
        if (h)
            dlclose(h);
        else {
            fprintf(stderr, "hull_breach: missing %s (install the %s package)\n", libs[i][0], libs[i][1]);
            ok = 0;
        }
    }
    return ok;
}

int main(void)
{
    if (sodium_init() < 0)
        return 1;
    if (!check_runtime_libs())
        return 1;
    SetTraceLogLevel(LOG_ERROR);
    InitWindow(W, H, "Rogue Swarm - Hull Breach");
    if (!IsWindowReady()) {
        fprintf(stderr, "cannot open window\n");
        return 1;
    }
    SetExitKey(KEY_Q);
    SetTargetFPS(render_fps());

    rng_s ^= (uint32_t)time(NULL);
    for (int i = 0; i < NSTARS; i++) {
        stars[i][0] = (float)(rnd() % W);
        stars[i][1] = (float)(rnd() % H);
    }
    reset_run();
    g_state = G_READY;

    /* Game logic steps at a fixed SIM_HZ; drawing runs at render_fps(). */
    double acc = 0;
    while (!WindowShouldClose()) {
        handle_input();
        acc += GetFrameTime();
        if (acc > 0.25)
            acc = 0.25;
        while (acc >= 1.0 / SIM_HZ) {
            if (!g_paused)
                update();
            acc -= 1.0 / SIM_HZ;
        }
        render();
    }
    CloseWindow();
    return 0;
}
