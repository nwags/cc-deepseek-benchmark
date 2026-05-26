# Plan: Git Server with Auto-Deploy to Web Server on Port 8080

## Context

User wants a git server at `/git/server` where a `git push` automatically deploys the latest content to a web server running on port 8080. The flow: `git clone` → edit files → `git commit` → `git push` → files appear at `http://server:8080/`.

## Steps

### 1. Install dependencies
- `apt-get install -y git python3` (neither is currently on the system)

### 2. Create the bare Git repository
- `git init --bare /git/server`
- This allows cloning via `git clone user@server:/git/server`

### 3. Configure the post-receive hook
- Write `/git/server/hooks/post-receive` to checkout the latest `master` branch into `/var/www/git-server` on every push:

```bash
#!/bin/bash
# Post-receive hook: deploy master to web root on every push
while read oldrev newrev refname; do
    if [ "$refname" = "refs/heads/master" ]; then
        GIT_WORK_TREE=/var/www/git-server git checkout -f master
        echo "Deployed to /var/www/git-server"
    fi
done
```

- `chmod +x /git/server/hooks/post-receive`
- Create the web root: `mkdir -p /var/www/git-server`

### 4. Set up a systemd service for the HTTP server
- Write `/etc/systemd/system/git-web.service`:
```
[Unit]
Description=Git-deployed web server on port 8080
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -m http.server 8080 -d /var/www/git-server
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```
- `systemctl daemon-reload`
- `systemctl enable --now git-web.service`

### 5. Verify
- `curl http://localhost:8080/` returns directory listing (empty initially)
- After a `git push master` with a `hello.html` file, `curl http://localhost:8080/hello.html` returns the file contents

## Files created/modified
- `/git/server/` — bare git repository (created by git)
- `/git/server/hooks/post-receive` — deploy hook
- `/var/www/git-server/` — web root (populated by the hook)
- `/etc/systemd/system/git-web.service` — HTTP server service
