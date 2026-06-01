# FH6 Tune Diagnosis Report

## Session
- Session: demo_udp_test
- Car: demo car
- Tune: baseline_001
- Use case: udp_demo
- Drivetrain: AWD
- Duration: 0.65 s
- Frames: 40
- Max speed: 116.76 km/h
- Avg speed: 108.88 km/h
- Best lap: N/A

## Main Findings
1. Possible understeer (high, 18 frames, 45.00% of data).

## Evidence
### Possible understeer
- front combined slip avg during events: 0.8233
- rear combined slip avg during events: 0.5927
- yaw rate abs avg during events: 0.2208 rad/s

## Suggested Tune Direction
- Slightly soften front anti-roll bar or stiffen rear anti-roll bar.
- Check front tire pressure and front camber if the pattern repeats.

## Data Quality Notes
- Treat diagnosis results as evidence prompts. Confirm with repeated runs on the same route.
- Mark runs with collisions, puddles, rewinds, or unusual route deviations before training models.
- Packet format reference: https://support.forza.net/hc/en-us/articles/51744149102611-Forza-Horizon-6-Data-Out-Documentation

## Machine Readable Findings
- `understeer`: `{'code': 'understeer', 'title': 'Possible understeer', 'severity': 'high', 'frame_count': 18, 'frame_rate': 0.45, 'evidence': ['front combined slip avg during events: 0.8233', 'rear combined slip avg during events: 0.5927', 'yaw rate abs avg during events: 0.2208 rad/s'], 'suggestions': ['Slightly soften front anti-roll bar or stiffen rear anti-roll bar.', 'Check front tire pressure and front camber if the pattern repeats.']}`
