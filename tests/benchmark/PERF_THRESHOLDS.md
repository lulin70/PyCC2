# Performance Thresholds

| Component | Threshold | Notes |
|-----------|-----------|-------|
| TerrainTileCache | 1000 tiles < 500ms | Cold cache |
| SurfacePool | 1000 cycles < 100ms | 64x64 SRCALPHA |
| ParticlePool | 500 cycles < 50ms | Acquire+release |
| Entity Resolution | 1000 entities < 200ms | Cold start |
