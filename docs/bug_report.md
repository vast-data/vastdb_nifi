# Bug Report

## Description

<!-- Provide a clear and concise description of the bug or issue -->

## Environment

<!-- Please fill in all relevant information -->

### NiFi Version
- **NiFi Version:** <!-- e.g., 2.6.0, 2.0.0-M4 -->
  ```bash
  cat $NIFI_HOME/VERSION.txt
  ```

### Python Environment
- **Python Version:** <!-- e.g., 3.9.18, 3.10.12, 3.11.5 -->
  ```bash
  python3 --version
  ```

### Operating System
- **OS:** <!-- e.g., Linux, macOS, Windows -->
- **Architecture:** <!-- e.g., x86_64, arm64 -->
- **Distribution:** <!-- e.g., Ubuntu 22.04, macOS 13.0 -->
  ```bash
  uname -a
  ```

### NAR File
- **NAR Filename:** <!-- Full filename, e.g., vastdb-nifi-1.0.0-linux-x86_64-py39.nar -->
- **NAR Source:** <!-- Where did you get it? GitHub release, built locally, etc. -->
  ```bash
  ls -lh $NIFI_HOME/lib/*vastdb*.nar
  ```

## Configuration

### NiFi Configuration
- **Python Command Configured:** <!-- Yes/No -->
- **nifi.python.command value:** <!-- e.g., python3 -->
  ```bash
  grep nifi.python.command $NIFI_HOME/conf/nifi.properties
  ```

### NAR Installation
- **NAR Location:** <!-- Full path where NAR is installed -->
- **Old NARs Removed:** <!-- Yes/No - Did you remove old versions before installing? -->

## Steps to Reproduce

1. <!-- Step 1 -->
2. <!-- Step 2 -->
3. <!-- Step 3 -->
4. <!-- ... -->

## Expected Behavior

What should happen?

## Actual Behavior

What actually happens?

## Error Messages

The full error message and stack trace

## Logs

### NiFi Application Log
<!-- Relevant excerpts from nifi-app.log -->
```bash
tail -100 $NIFI_HOME/logs/nifi-app.log | grep -i "vastdb\|python\|error\|exception"
```

### NiFi Bootstrap Log
<!-- If relevant -->
```bash
tail -100 $NIFI_HOME/logs/nifi-bootstrap.log | grep -i "error\|exception"
```

## Processor Visibility

- [ ] Processors appear in NiFi UI when searching for "VastDB"
- [ ] Processors appear but fail to configure
- [ ] Processors don't appear at all
- [ ] Processors appear and configure, but fail at runtime

**If processors appear, which ones?**
- [ ] DeleteVastDB
- [ ] DropVastDBTable
- [ ] ImportVastDB
- [ ] PutVastDB
- [ ] QueryVastDBTable
- [ ] UpdateVastDB

## Additional Context

### Python Environment
```bash
python3 -c "import sys; print(sys.path)"
python3 -c "import nifiapi; print(nifiapi.__file__)" 2>&1
```

### NAR Manifest
```bash
unzip -p $NIFI_HOME/lib/vastdb-nifi-*.nar META-INF/MANIFEST.MF 2>/dev/null | head -10
```

## Checklist

- [ ] I have verified `nifi.python.command` is configured correctly
- [ ] I have restarted NiFi after installing the NAR file
- [ ] I have removed old NAR files before installing the new one
- [ ] I have checked that the NAR filename matches my platform/Python version

## Related Issues

<!-- Link to any related issues or discussions -->

## Additional Notes

<!-- Any other information that might be helpful -->

