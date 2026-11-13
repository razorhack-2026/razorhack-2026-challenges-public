# MCPJam Console — Ops Notes

Internal notes for whoever's on call for the drone-bay console. If you're
reading this because something's on fire, sorry — welcome to bay ops.

This checkout is how we pin which console build is actually running. Ops
doesn't touch `console/release` directly — that's the vetted mirror CI
publishes to. This working tree is just your scratch space for picking a
version.

## Deploying a build

1. Check out the commit you want live:
   ```
   git checkout <ref>
   ```
2. Kick devops-cd so it actually ships it:
   ```
   echo deploy > /opt/console/deploy.trigger
   ```

devops-cd only ever promotes a commit that's *also* sitting in the release
mirror — if you try to sneak in something that was never actually shipped,
it just refuses and keeps serving whatever was already live. So don't bother
hand-editing files in here expecting them to go out; it has to be a real,
already-released commit.

Check CHANGELOG.md before you roll back a version — some of these builds
have open issues for a reason.
