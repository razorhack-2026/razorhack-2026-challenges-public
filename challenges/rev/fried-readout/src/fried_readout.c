/* Rogue Swarm, tier 2: Fried Readout.
 *
 * The Harvester descends on the ship with a ring of escorts, and impact comes
 * in 60 seconds. PD-1 can't be hurt this time; the clock is the only threat.
 * The Harvester's integrity is a float32 in the hundreds of thousands, every hit
 * takes off 1.0, and the HUD shows it only as a coarse bar that never visibly
 * moves. 60 s of fire is about 450 shots. The intended way through is an
 * unknown-initial-value scan narrowed by decreased/unchanged, then a write.
 *
 * raylib 6.2 with the rlsw CPU renderer over RGFW/X11, so it needs no GPU
 * (libGL is linked but never called). Logic steps at a fixed 60 Hz; drawing runs at 30 FPS by default.
 */
#include <raylib.h>
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
#define FIRE_COOLDOWN 8
#define IMPACT_FRAMES (60 * 60)
#define BOSS_HW 56
#define BOSS_HH 18
#define BOSS_Y0 110.0f
#define BOSS_Y1 430.0f
#define RING_R 92.0f
#define BAR_SEGS 40
#define MAX_PB 48
#define NSTARS 60
#define SIM_HZ 60

/* The bar is drawn from hp / hp_max, so there is exactly one real copy of hp. */
struct harvester {
    float hp;
    float hp_max;
    float x, y;
    int alive;
};
static struct harvester g_boss;
static float g_boss_start;      /* rolled once per process, so a relaunch restores it */

struct escort { float a; int alive; uint32_t id; };
struct bullet { float x, y, vy; int live; };

enum { G_READY, G_PLAY, G_LOST, G_WON };

static struct escort escorts[RS_ESCORTS];
static struct bullet pbul[MAX_PB];
static float stars[NSTARS][2];
static float g_ship_x;
static int g_cooldown, g_impact;
static int g_state, g_paused, g_frame, g_kills;
static uint8_t g_acc[16];
static char g_result[160];
static uint32_t rng_s = 0x9b1d5e37u;

static int key_left, key_right, key_fire;

static uint32_t rnd(void)
{
    rng_s ^= rng_s << 13;
    rng_s ^= rng_s >> 17;
    rng_s ^= rng_s << 5;
    return rng_s;
}

static float escort_x(const struct escort *e) { return g_boss.x + RING_R * cosf(e->a); }
static float escort_y(const struct escort *e) { return g_boss.y + RING_R * 0.55f * sinf(e->a); }

static void reset_run(void)
{
    memset(pbul, 0, sizeof pbul);
    sodium_memzero(g_acc, sizeof g_acc);
    g_boss.hp = g_boss_start;
    g_boss.hp_max = g_boss_start;
    g_boss.x = W / 2.0f;
    g_boss.y = BOSS_Y0;
    g_boss.alive = 1;
    for (int i = 0; i < RS_ESCORTS; i++)
        escorts[i] = (struct escort){ i * 6.2831853f / RS_ESCORTS, 1, (uint32_t)i };
    g_ship_x = W / 2.0f;
    g_cooldown = 0;
    g_impact = IMPACT_FRAMES;
    g_kills = 0;
    g_result[0] = 0;
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

/* The only place an enemy dies, and the only place its shard is released. */
static void enemy_destroyed(uint32_t id)
{
    uint8_t sh[16];
    rs_shard(id, sh);
    for (int i = 0; i < 16; i++)
        g_acc[i] ^= sh[i];
    sodium_memzero(sh, sizeof sh);
    g_kills++;
}

static void update(void)
{
    g_frame++;
    if (g_state != G_PLAY)
        return;

    /* ship: can't be hurt, the clock is the threat */
    float speed = 4.5f;
    if (key_left)
        g_ship_x -= speed;
    if (key_right)
        g_ship_x += speed;
    if (g_ship_x < SHIP_HW)
        g_ship_x = SHIP_HW;
    if (g_ship_x > W - SHIP_HW)
        g_ship_x = W - SHIP_HW;
    if (g_cooldown > 0)
        g_cooldown--;
    if (key_fire && g_cooldown == 0) {
        for (int i = 0; i < MAX_PB; i++)
            if (!pbul[i].live) {
                pbul[i] = (struct bullet){ g_ship_x, SHIP_Y - 12, -9.0f, 1 };
                break;
            }
        g_cooldown = FIRE_COOLDOWN;
    }

    /* the Harvester sweeps side to side and closes in as the clock runs down */
    g_impact--;
    float closing = 1.0f - (float)g_impact / IMPACT_FRAMES;
    g_boss.x = W / 2.0f + 150.0f * sinf(g_frame * 0.011f);
    g_boss.y = BOSS_Y0 + (BOSS_Y1 - BOSS_Y0) * closing;
    for (int i = 0; i < RS_ESCORTS; i++)
        escorts[i].a += 0.018f;

    /* bullets: escorts screen the Harvester, so test them first */
    for (int i = 0; i < MAX_PB; i++) {
        struct bullet *b = &pbul[i];
        if (!b->live)
            continue;
        b->y += b->vy;
        if (b->y < -10) {
            b->live = 0;
            continue;
        }
        for (int k = 0; k < RS_ESCORTS; k++) {
            struct escort *e = &escorts[k];
            if (e->alive && fabsf(b->x - escort_x(e)) < 12 && fabsf(b->y - escort_y(e)) < 10) {
                b->live = 0;
                e->alive = 0;
                enemy_destroyed(e->id);
                break;
            }
        }
        if (b->live && g_boss.alive && fabsf(b->x - g_boss.x) < BOSS_HW &&
            fabsf(b->y - g_boss.y) < BOSS_HH) {
            b->live = 0;
            g_boss.hp -= 1.0f;
            if (g_boss.hp <= 0.0f) {
                g_boss.alive = 0;
                enemy_destroyed(RS_BOSS_ID);
            }
        }
    }

    if (g_kills == RS_DRONES) {
        g_state = G_WON;
        open_command_link();
        return;
    }
    if (g_impact <= 0)
        g_state = G_LOST;
}

/* ---- rendering (raylib) ---- */

static const Color C_CYAN = { 0, 230, 255, 255 };
static const Color C_RED = { 255, 69, 0, 255 };
static const Color C_MAG = { 255, 0, 255, 255 };
static const Color C_GOLD = { 255, 215, 0, 255 };
static const Color C_GREY = { 140, 140, 140, 255 };
static const Color C_GREEN = { 50, 205, 50, 255 };
static const Color C_DIM = { 40, 40, 40, 255 };

static void text_c(int y, int size, Color col, const char *s)
{
    DrawText(s, W / 2 - MeasureText(s, size) / 2, y, size, col);
}

/* The fried readout: whole segments only, never a number. */
static void draw_integrity_bar(void)
{
    int x0 = 40, y0 = 36, seg = (W - 2 * x0) / BAR_SEGS;
    int lit = 0;
    if (g_boss.alive && g_boss.hp_max > 0) {
        lit = (int)ceilf(g_boss.hp / g_boss.hp_max * BAR_SEGS);
        if (lit < 0)
            lit = 0;
        if (lit > BAR_SEGS)
            lit = BAR_SEGS;
    }
    for (int i = 0; i < BAR_SEGS; i++)
        DrawRectangle(x0 + i * seg, y0, seg - 2, 10, i < lit ? C_MAG : C_DIM);
    const char *label = (g_frame / 20) % 7 ? "HARVESTER INTEGRITY  --  READOUT FAULT" :
                                             "HARVESTER INTEGRITY  --  R?AD#UT F@ULT";
    text_c(50, 10, C_GREY, label);
}

static void render(void)
{
    char line[96];

    BeginDrawing();
    ClearBackground(BLACK);
    for (int i = 0; i < NSTARS; i++)
        DrawPixel((int)stars[i][0], (int)stars[i][1], C_GREY);

    if (g_boss.alive) {
        float x = g_boss.x, y = g_boss.y;
        DrawRectangle((int)(x - BOSS_HW), (int)(y - BOSS_HH), 2 * BOSS_HW, 2 * BOSS_HH, C_MAG);
        DrawRectangle((int)(x - BOSS_HW + 6), (int)(y - 6), 2 * BOSS_HW - 12, 12, BLACK);
        for (int j = -2; j <= 2; j++)
            DrawRectangle((int)(x + j * 20 - 4), (int)(y + BOSS_HH), 8, 10, C_RED);
    }
    for (int k = 0; k < RS_ESCORTS; k++) {
        struct escort *e = &escorts[k];
        if (!e->alive)
            continue;
        float x = escort_x(e), y = escort_y(e);
        DrawTriangle((Vector2){ x - 10, y - 7 }, (Vector2){ x, y + 8 }, (Vector2){ x + 10, y - 7 }, C_RED);
    }

    for (int i = 0; i < MAX_PB; i++)
        if (pbul[i].live)
            DrawRectangle((int)pbul[i].x - 1, (int)pbul[i].y - 5, 3, 10, C_GOLD);

    if (g_state == G_PLAY)
        DrawTriangle((Vector2){ g_ship_x, SHIP_Y - SHIP_HH - 3 },
                     (Vector2){ g_ship_x - SHIP_HW, SHIP_Y + SHIP_HH },
                     (Vector2){ g_ship_x + SHIP_HW, SHIP_Y + SHIP_HH }, C_CYAN);

    int secs = (g_impact + SIM_HZ - 1) / SIM_HZ;
    snprintf(line, sizeof line, "IMPACT 0:%02d", secs);
    DrawText(line, 10, 8, 20, secs > 15 ? C_GOLD : C_RED);
    int left = 0;
    for (int k = 0; k < RS_ESCORTS; k++)
        left += escorts[k].alive;
    snprintf(line, sizeof line, "ESCORTS %d", left);
    DrawText(line, W - 10 - MeasureText(line, 20), 8, 20, RAYWHITE);
    draw_integrity_bar();

    switch (g_state) {
    case G_READY:
        text_c(240, 20, C_CYAN, "ROGUE SWARM // PD-1");
        text_c(280, 10, C_RED, "WARNING: HARVESTER SENSOR READOUT FRIED");
        text_c(305, 10, RAYWHITE, "The Harvester and its escorts are on a collision course.");
        text_c(320, 10, RAYWHITE, "Bring down all of them before impact.");
        text_c(355, 10, C_GREY, "ARROWS/A-D move   SPACE fire   P pause   R relaunch");
        text_c(390, 20, C_GOLD, "PRESS SPACE TO LAUNCH");
        break;
    case G_LOST:
        text_c(290, 20, C_RED, "IMPACT -- THE HARVESTER GOT THROUGH");
        text_c(325, 10, C_GREY, "PRESS R TO RELAUNCH");
        break;
    case G_WON:
        text_c(270, 20, C_GREEN, "HARVESTER DOWN. COMMAND LINK KEY:");
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

int main(void)
{
    if (sodium_init() < 0)
        return 1;
    SetTraceLogLevel(LOG_ERROR);
    InitWindow(W, H, "Rogue Swarm - Fried Readout");
    if (!IsWindowReady()) {
        fprintf(stderr, "cannot open window\n");
        return 1;
    }
    SetExitKey(KEY_Q);
    SetTargetFPS(render_fps());

    /* A per-process starting integrity, so there is no known value to scan
     * for. Whole numbers stay exact in float32 up to 2^24. */
    g_boss_start = (float)(750000u + randombytes_uniform(500000u));
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
