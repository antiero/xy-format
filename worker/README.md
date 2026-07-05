# XYBuddy Stats Worker

Cloudflare Worker for the anonymous aggregate OP-XY steps counter.

Before deploying, create a KV namespace and replace the placeholder
`XYBUDDY_STATS` ids in `wrangler.toml`.

```sh
npm ci
npm run check
npm run deploy
```

The Worker should be available at `https://api.xybuddy.xyz`.
