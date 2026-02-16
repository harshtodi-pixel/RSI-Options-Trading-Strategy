# Backtest Summary

**Period**: 2025-01-01 to 2025-12-31

## Strategy

- **Signal**: Sell ATM option when RSI(14) crosses above 70
- **RSI**: Calculated on continuous ATM option price (not underlying), fresh each day
- **Entry**: Staggered at +5% / +10% / +15% (33.33% each)
- **Stop Loss**: 20% (exact fill assumed)
- **Target**: 10% (exact fill assumed)
- **Hours**: 09:30 - 14:30 IST
- **Expiry**: Nearest weekly (expiry_code = 1)
- **Strikes**: ATM only
- **Intraday**: Signals expire at EOD, positions force-closed at EOD
- **Capital**: Rs 200,000 per instrument

---

## Combined Results

| Metric | Value |
|--------|-------|
| Total Capital Deployed | Rs 400,000 |
| Total Money P&L | Rs 537,286.84 |
| Combined Return | 134.32% |
| Total Trades | 2579 |
| Total Wins | 2019 (78.3%) |

---

## NIFTY (Lot Size: 75)

### Performance

| Metric | Value |
|--------|-------|
| Initial Capital | Rs 200,000 |
| Final Capital | Rs 487,473 |
| Money P&L | Rs 287,473.47 |
| Return | 143.74% |
| Option P&L (points) | Rs 3,832.98 |

### Trade Statistics

| Metric | Value |
|--------|-------|
| Total Trades | 1377 |
| Wins | 1073 (77.9%) |
| Losses | 304 |
| Avg P&L per Trade | Rs 208.77 |
| Avg Win | Rs 698.87 |
| Avg Loss | Rs -1,521.10 |
| Max Win | Rs 2,659.40 |
| Max Loss | Rs -4,398.92 |

### Exit Reasons

| Reason | Count | % |
|--------|-------|---|
| Target | 1040 | 75.5% |
| Stop Loss | 275 | 20.0% |
| EOD | 62 | 4.5% |

### By Option Type

| Type | Trades | Money P&L |
|------|--------|----------|
| CE | 656 | Rs 130,563.23 |
| PE | 721 | Rs 156,910.24 |

### Entry Fill Breakdown

| Parts Filled | Count |
|-------------|-------|
| 1/3 | 508 |
| 2/3 | 243 |
| 3/3 | 626 |
| Avg Parts | 2.09 |

---

## SENSEX (Lot Size: 20)

### Performance

| Metric | Value |
|--------|-------|
| Initial Capital | Rs 200,000 |
| Final Capital | Rs 449,813 |
| Money P&L | Rs 249,813.37 |
| Return | 124.91% |
| Option P&L (points) | Rs 12,490.67 |

### Trade Statistics

| Metric | Value |
|--------|-------|
| Total Trades | 1202 |
| Wins | 946 (78.7%) |
| Losses | 256 |
| Avg P&L per Trade | Rs 207.83 |
| Avg Win | Rs 614.42 |
| Avg Loss | Rs -1,294.66 |
| Max Win | Rs 2,393.94 |
| Max Loss | Rs -3,283.51 |

### Exit Reasons

| Reason | Count | % |
|--------|-------|---|
| Target | 910 | 75.7% |
| Stop Loss | 227 | 18.9% |
| EOD | 65 | 5.4% |

### By Option Type

| Type | Trades | Money P&L |
|------|--------|----------|
| CE | 553 | Rs 98,852.41 |
| PE | 649 | Rs 150,960.96 |

### Entry Fill Breakdown

| Parts Filled | Count |
|-------------|-------|
| 1/3 | 444 |
| 2/3 | 231 |
| 3/3 | 527 |
| Avg Parts | 2.07 |

