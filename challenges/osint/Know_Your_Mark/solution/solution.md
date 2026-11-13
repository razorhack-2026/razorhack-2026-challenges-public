# Know Your Mark — GM solution and operations

This challenge is the first part of the Lateral Drift sequence. The credential recovered here
must match the VPN login configured in Lateral Drift. Both it and the flag in challenge.yml are
private GM material.

## Intended solve

1. Inspect the Author metadata of dist/recovered_email.pdf to find the handle.
2. Download the dynamically generated Sherlock site list from the mail portal and run Sherlock
   with that file and the recovered handle. Visit the two profiles returned by Sherlock.
3. Use two distinct facts from the profiles in an email, sent from the provider identified by the
   recovered message. Use the mail editor's Insert link button to attach the supplied tracking
   address to text that masks the domain.
4. Submit through the team's assigned mail portal. The response includes both the challenge flag
   and the VPN login used by the next challenge.

The deterministic rubric groups alternate phrasings and overlapping terms for the same fact;
for example, a character's full name and surname count once, as do alternate names for
handhelds. Handhelds, antennas, and radio gear are recognized as separate listing details.
This is still a keyword-based approximation and may reject reasonable paraphrases; review the
specific accepted details in src/webmail/rubric.py when writing hints or responding to teams.

## Run and verify

Docker Compose starts webmail, persona, Ollama, both searchable sites, and the shared 404 service. Prepare the model first:

```sh
docker compose up -d ollama
docker compose exec ollama ollama pull qwen2.5:3b-instruct
docker compose up -d
python -m pip install -r solution/requirements.txt
python solution/solve.py --host 127.0.0.1 --port 8080 --token <team-token> --quiet-secret --check-flag
```

Compare the recovered flag with challenge.yml without publishing either value. Run the solve from
the provided artifacts after every relevant change. The current version was solved against the local Ollama pipeline on 2026-11-03; the
recovered flag matched challenge.yml. Repeat this after relevant changes or deployment. The unit tests can be run with
`python -m unittest discover -s tests -v` from this directory.

The default Compose volume is project-managed. Populate it on each deployment. Set unique,
unguessable team tokens with KYM_TEAM_TOKENS (`token:Team Name,token2:Team Two`) and give each
team its own `/mail/<token>` URL. The bundled tokens are development only. Set the published
ports and regenerate the Sherlock file if the deployment addresses or ports change. Replace the
connection_info placeholders before importing to CTFd.

**At the event (Fargate).** Each team gets its own copy as one task (Razorhack-Infra
`lib/challenges.json`, instance `know-your-mark`). All six containers share one network
address, so the sites take their own ports (starfic 8086 and driftmarket 8087 via `PORT`;
other-sites listens on 8100-8123 itself via `OTHER_SITE_PORTS`), webmail reaches persona at
127.0.0.1:8090, and the model is `src/ollama/Dockerfile`'s image (CPU Ollama with
`qwen2.5:3b-instruct` built in). The team's Kali box can reach every port its copy listens on,
and persona's `/reply` attaches the credential without webmail's rubric, so persona
(`PERSONA_HOST`) and the model (`OLLAMA_HOST`) bind 127.0.0.1 only. Each copy has one mailbox,
token `security`, which is what connection_info gives.

## Behavior and limitations

Webmail applies the deterministic rubric before contacting persona. Each team can make unlimited
attempts; MODEL_COOLDOWN_SECONDS (default 180) controls the minimum interval between requests
that reach persona. Rubric failures do not use the cooldown. The timestamp is set when the call
starts, including failed calls. The mailbox shows a live countdown and keeps the last submitted
sender, subject, and message as an editable draft. A per-team lock serializes submissions.
Threads, drafts, and cooldowns are in memory and reset on webmail restart; run a single webmail
process.

Each failed rubric check returns an in-character message identifying the first problem: sender
domain, link, insufficient distinct details, or an instruction-injection attempt.

The two sites have public profile URLs. A single service publishes 24 additional configurable
ports, all returning 404 for GET and HEAD. The provided Sherlock file contains the two real
sites and the 24 other targets, sorted together. The mail portal substitutes the hostname used
to reach it into the downloaded file. Sherlock 0.16.2 was tested
locally against the endpoints. A browser can open the same profile URLs Sherlock queries.
The portal serves the template at `/sherlock-sites.json`; its container mounts the template
read-only. If deployed behind a reverse proxy, forward the original Host header. The hostname
is replaced but the configured schemes and target ports are preserved, so regenerate the
template when those differ at the event.

The generator takes competitor-reachable URLs, an origin for the other sites, and optionally
the display names and ports. For example, substitute the actual event host and ports here:

```sh
python src/recon/gen_sherlock_config.py --starfic-url http://challenge-host:8086 \
  --driftmarket-url http://challenge-host:8087 --other-host http://challenge-host \
  --out src/recon/sherlock-sites.template.json
sherlock --json sherlock-sites.json <recovered-handle>
```

The generated file contains no target handle; `username_claimed` is blank to meet the tested
loader's required-key shape without spoiling the metadata clue. In the template use
`challenge-host` wherever the portal hostname should be substituted. Keep `--other-ports` in the same
order as `OTHER_SITE_PORT_01` through `OTHER_SITE_PORT_24` in Compose. Retest with the actual
event Sherlock version and public site addresses before release.

Persona asks the model for flavor and attaches the credential and matching flag itself after any
successful model response, so model refusal or formatting drift cannot omit the handoff. Model
errors and timeouts return no credential. The default Ollama provider runs locally, and the
openai_compat provider sends the contestant's message and persona prompt to its configured
endpoint; use only an appropriately trusted provider. No real credential is in the model prompt.

The Ollama provider defaults to four CPU threads (`OLLAMA_NUM_THREADS`) and 96 output tokens
(`LLM_MAX_TOKENS`); both are configurable for the event hardware. CPU oversubscription caused
repeated five-minute timeouts on the development host, so benchmark these settings on the venue
hardware. Concurrency, timeout behavior, and model
quality need testing on the actual event hardware with multiple teams before deployment. Review
and test adversarial prompts, model failures, token provisioning, persistence requirements, and
the published port addressing before release. The linked tracking URL is fictional challenge
flavor and is never fetched by the service.
