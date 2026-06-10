# FUT Market Playbook

Trading intelligence for the EA FC Ultimate Team transfer market, with the exact `cli-web-futbin` commands to execute each strategy.

## Table of Contents

1. [Weekly Market Cycle](#weekly-market-cycle)
2. [EA Tax & Profit Formulas](#ea-tax--profit-formulas)
3. [Promo Calendar & Crash Windows](#promo-calendar--crash-windows)
4. [Fodder Investment Rules](#fodder-investment-rules)
5. [Mass Bidding](#mass-bidding)
6. [Signal Interpretation](#signal-interpretation)
7. [Strategy Walkthroughs](#strategy-walkthroughs)
8. [Daily and Event Workflows](#daily-and-event-workflows)

---

## Weekly Market Cycle

The transfer market follows a weekly rhythm driven by game modes and reward drops. This is the single biggest edge for consistent profit.

| Day | What happens | Action |
|-----|-------------|--------|
| Monday | Slow market, low activity post-Weekend League | BUY — prices stable/low |
| Tuesday | Still quiet; 6PM content rarely market-moving | BUY — accumulate targets |
| Wednesday | Midweek crash: FUT Champions squads sold off | BUY — best window of the week |
| Thursday AM | Division Rivals rewards flood the market with pack pulls | BUY the dip (prices drop 5–10%) |
| Thursday PM | Reward coins chase Weekend League squads | HOLD or start listing |
| Friday | Weekend League demand peaks | SELL — prime window |
| Saturday | Late WL squad additions, weekly price high | SELL — peak prices |
| Sunday | Squad Battles rewards + post-WL sell-off late night | BUY late evening |

```bash
# Wednesday/Thursday — find buy targets
cli-web-futbin market scan --rating-min 85 --rating-max 89 --threshold 10 --json
cli-web-futbin market movers --fallers --rating-min 84 --min-price 2000 --json

# Friday — confirm a hold has risen before selling
cli-web-futbin market analyze <player_id> --json   # sell if trend_7d positive AND vs_avg_30d_pct > 5

# Sunday night — post-WL crash buys
cli-web-futbin market movers --fallers --rating-min 86 --min-price 5000 --max-price 100000 --json
```

## EA Tax & Profit Formulas

Every sale incurs a 5% EA tax, on all platforms.

| Concept | Formula | Example |
|---------|---------|---------|
| Net return | `Sale × 0.95` | 100K sale → 95K |
| Break-even sell price | `Buy / 0.95` | Bought at 10K → sell at 10,527+ |
| Profit | `(Sell × 0.95) − Buy` | Buy 10K, sell 15K → 4,250 |
| Margin % | `Profit / Buy × 100` | 4,250 / 10K = 42.5% |

Minimum viable margins by tier: 1–5K cards need 10–15% margin (high volume); 5–20K is the mass-bidding sweet spot; 100K+ flips carry tax of 5–25K coins, so demand bigger gaps; 500K+ is high risk — a 3% market wobble plus tax wipes profit.

**New-card pricing trap:** launch prices are hype-inflated. Ignore the first 7–14 days of price history; don't trust `price_position_pct` on cards under 2 weeks old; check `market latest` — if a card appears there, treat all signals with caution and use `players get <id>` `price_range.min` (EA's floor) for context instead.

```bash
# Find cards with enough margin to clear the tax (15%+ below 30d average)
cli-web-futbin market scan --rating-min 84 --threshold 15 --json
```

## Promo Calendar & Crash Windows

Promos crash the market because special packs flood supply. Sell before, buy during. Typical FC-cycle schedule:

| Promo | Window | Impact | Strategy |
|-------|--------|--------|----------|
| TOTY | mid-Jan – Feb | Biggest crash of the year; meta cards −30–50% | Sell meta by ~Jan 10, buy in the Jan 22–30 trough |
| Future Stars | Feb | Moderate crash on young meta cards | Buy after the initial dip settles |
| FUT Birthday | early–mid Mar | Icon SBCs spike fodder, then crash | Sell fodder before it starts; buy promo cards during |
| Fantasy FC | Feb–May | Gradual; live items upgrade over time | Buy live items early, sell on upgrades |
| TOTS | May–Jun | Second biggest crash; 90+ cards become common | Sell all high-rated cards before; buy at the bottom |
| Shapeshifters | Jun–Jul | Position changes create new meta | Buy cheap versions of shifted players pre-hype |
| Futties | Jul–Aug | End of cycle, annual price floor | Buy whatever you want to use |
| Black Friday | late Nov | Short, intense; lightning rounds | Sell the Wednesday before; buy Thu–Fri |

```bash
# Pre-crash checklist
cli-web-futbin market analyze <player_id> --json     # sell holds with price_position_pct > 60
cli-web-futbin market index --json                   # falling indices across tiers = crash starting
cli-web-futbin market fodder --rating-min 84 --json  # inflated fodder (84s > 5K)? sell before promo

# During the crash — find the deepest dips
cli-web-futbin market movers --fallers --rating-min 88 --min-price 10000 --json
cli-web-futbin market scan --rating-min 86 --rating-max 90 --threshold 20 --json
```

## Fodder Investment Rules

Fodder = high-rated cards (83–91) used as SBC fuel. The safest, most repeatable money-maker.

Cycle: no active SBCs → fodder cheap → **buy** → popular SBC drops (Icon, POTM, upgrades) → demand spikes → **sell** → promo pack-opening floods supply → crash → **buy again**.

Rules:
1. 84–87 rated is the sweet spot (consistent SBC demand, manageable risk; 83 = tiny margins, 88+ = slower and more volatile).
2. Buy when no SBCs are active; sell when a popular SBC drops.
3. Sell before promos start — pack openings crash fodder within hours.
4. Never hold fodder through TOTY or TOTS.
5. Diversify across rating tiers.

```bash
cli-web-futbin market fodder --json                                   # current floor at each tier
cli-web-futbin market index --rating 84 --json                        # near "lowest" = buy, near "highest" = sell
cli-web-futbin market cheapest --rating-min 85 --rating-max 85 --json # cheapest cards at a tier
cli-web-futbin market movers --rating-min 83 --min-price 500 --max-price 20000 --json  # your tiers rising? sell now
```

## Mass Bidding

Place 50–100+ bids 10–20% below lowest BIN on liquid 2K–10K, 83–86 rated gold rares; win ~30–40%; relist just under BIN.

Worked example: lowest BIN 5,000 → bid 4,200 → relist 4,900 → 4,655 after tax → ~455 profit per card → ~18 wins per 50 bids ≈ 8K coins per round.

```bash
# Find liquid targets in the sweet spot
cli-web-futbin market cheapest --rating-min 83 --rating-max 86 --min-price 2000 --max-price 10000 --json
cli-web-futbin market popular --limit 50 --json     # high views = faster sales
cli-web-futbin market analyze <player_id> --json    # good target: volatility_30d < 15, price_position_pct < 40
```

## Signal Interpretation

`market analyze` returns a `signal`:

| Signal | Trigger | Act when | Ignore when |
|--------|---------|----------|-------------|
| BUY | >10% below 30d avg, 7d trend stable/rising | You understand the dip (crash, rewards day) | The card is being superseded by a better version |
| SELL | >15% above 30d avg, 7d trend falling | You hold for profit — the bubble is deflating | A major SBC just dropped and demand is still rising |
| HOLD | Near average | Wait 1–2 days and re-check | You have time-sensitive info (promo incoming, SBC expiring) |

Combine the signal with context before acting: day of week (cycle), promo calendar, active SBC demand (`sbc list`), and whether the whole market is moving (`market index`) or just this card.

## Strategy Walkthroughs

**1. Buy the dip**
```bash
cli-web-futbin market scan --rating-min 85 --rating-max 89 --threshold 10 --json
cli-web-futbin market analyze <player_id> --json   # buy if signal=BUY, price_position_pct < 15, trend_7d positive
```

**2. SBC fodder trading**
```bash
cli-web-futbin market fodder --json
cli-web-futbin market cheapest --rating-min 85 --rating-max 85 --json
cli-web-futbin market movers --rating-min 84 --min-price 1000 --max-price 20000 --json  # SBC dropped? confirm the spike
```

**3. Cross-platform arbitrage**
```bash
cli-web-futbin market arbitrage --rating-min 88 --min-gap 10 --json
cli-web-futbin market analyze <player_id> --json   # sanity-check liquidity and trend
```

**4. Version value hunting**
```bash
cli-web-futbin players versions --name "Salah" --json          # highest value_score = best stats per 1K coins
cli-web-futbin players compare <base_id> <special_id> --json
```

**5. Crash detection**
```bash
cli-web-futbin market movers --fallers --rating-min 88 --min-price 10000 --json
cli-web-futbin market index --json                 # market-wide or card-specific?
cli-web-futbin market index --rating 88 --json
```

**6. Trending flip**
```bash
cli-web-futbin market popular --limit 30 --json
cli-web-futbin market analyze <trending_id> --json # buy if signal=BUY/HOLD and price_position_pct < 30
```

## Daily and Event Workflows

**Daily routine (10 min):**
```bash
cli-web-futbin market index --json                                       # 1. market health
cli-web-futbin market movers --rating-min 84 --min-price 2000 --json     # 2. risers
cli-web-futbin market movers --fallers --rating-min 84 --min-price 2000 --json  #    fallers
cli-web-futbin market latest --json                                      # 3. new cards
cli-web-futbin market popular --limit 20 --json                          # 4. hype check
cli-web-futbin market fodder --rating-min 84 --rating-max 88 --json      # 5. fodder timing
cli-web-futbin market scan --rating-min 85 --rating-max 89 --limit 10 --json  # 6. deals
```

**Pre-promo prep (3–5 days out):** analyze every high-value hold (sell at `price_position_pct > 40` or negative `trend_30d`), check indices for early deflation, research post-crash targets with `players versions`, sell inflated fodder, and check `market arbitrage --min-gap 10` — gaps widen pre-promo.

**Post-crash buying:** compare index `current` vs `open` for crash depth, buy the biggest 87+ fallers showing oversold signals (`price_position_pct < 10`, `vs_avg_30d_pct < -20`, 7d trend stabilizing), bulk-scan with `--threshold 15`, and load up on fodder if 84s < 1.5K / 85s < 3K.

**Fodder cycle (bread and butter):** identify (fodder + index near lows) → buy cheapest at each tier 84–86, diversified → monitor `sbc list` daily → sell into the spike when movers show your tiers rising and `vs_avg_30d_pct > 10`. Take 10–20% — don't chase the absolute peak.
