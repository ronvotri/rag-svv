# Wave 34 Web Beta — release branch

Owner requested deploying the updated Beta to the existing Web site and
asked to reuse prior GitHub write access rather than manual workflow dispatch.
Build #8 and #9 passed direct-base 0.2.11 export, Pages staging and initial
splash checks. This release-only commit restores the existing push-triggered
release route, restricted to changes to the publish workflow itself.
The existing RAGNAROK_AUTO_DEPLOY_WEB repository opt-in remains mandatory for
push releases; the web-production environment and existing Cloudflare
credentials remain unchanged. No variables, secrets or approvals are modified.
Manual publication also retains its explicit rights checkbox.
The release branch is advanced without force, from the verified ancestor.
Browser and real player Save QA are not yet confirmed. Beta uses a separate
profile; old data is not deleted or migrated. NPC portrait likeness is not
approved. Do not treat workflow initiation as successful deployment.
