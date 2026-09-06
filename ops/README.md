# Ops

launchd **agents** (Aqua only), not daemons.

```
cp ops/launchd/com.jarvis.brain.plist ~/Library/LaunchAgents/
cp ops/launchd/com.jarvis.jarvisd.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.jarvis.brain.plist
launchctl load ~/Library/LaunchAgents/com.jarvis.jarvisd.plist
```

`wired_limit.sh` prints `mx.metal.device_info()` and the sysctl to raise GPU wired memory. Refuses SSH.
