# Overlap by IDF band

Split `test`, `labels_desc`, stemmed, stopwords removed. The same query-to-gold overlap as experiment 03, split by how discriminative each term is. Bands are quantiles of the corpus vocabulary by IDF, so a term sits in the same band for every query.
Intervals are 95% percentile bootstrap over queries.

## Gold vocabulary covered by the query, per band

| band | pt | en | en advantage | pt gold terms | en gold terms |
|---|---|---|---:|---:|---:|
| df 1 | 0.0159 [0.0095, 0.0235] | 0.0140 [0.0085, 0.0204] | -11.9% | 5 | 6 |
| df 2 to 5 | 0.0312 [0.0244, 0.0391] | 0.0237 [0.0179, 0.0305] | -23.9% | 9 | 10 |
| df 6 to 50 | 0.0447 [0.0413, 0.0482] | 0.0452 [0.0412, 0.0493] | +1.2% | 52 | 53 |
| df 51+ | 0.0794 [0.0761, 0.0828] | 0.0719 [0.0690, 0.0749] | -9.5% | 153 | 176 |

English advantage in the rarest band is -9.5%, against -23.9% to +1.2% in the commoner bands.

## What the bands contain

Most frequent terms in each band, to show what the split is separating.

**pt**

- *df 1*: `correcional` `agind` `repress` `toxicológ` `bairr` `debulh` `ceifeir` `massific`
- *df 2 to 5*: `correcion` `enzim` `reagent` `diplomát` `exij` `suspensã` `convenc` `portuári`
- *df 6 to 50*: `inic` `adquir` `sempr` `vez` `exat` `disponibil` `individual` `expediçã`
- *df 51+*: `utiliz` `equip` `process` `produt` `fim` `aplic` `outr` `sobr`

**en**

- *df 1*: `oppres` `oppress` `inferior` `treatement` `warmer` `erm` `headstock` `fretboard`
- *df 2 to 5*: `misus` `reagent` `activit` `solo` `concert` `spontan` `policymak` `bespok`
- *df 6 to 50*: `roll` `fund` `agricultur` `day` `seek` `behavior` `radiat` `transmiss`
- *df 51+*: `use` `perform` `oper` `product` `manag` `process` `ensur` `make`

## Reading this

Rare terms carry most of a BM25 score. If Portuguese coverage matches English on common terms and falls behind on rare ones, then the two languages share comparable vocabulary overall while diverging precisely where ranking is decided. That is what inconsistent translation of technical terminology would produce, and it is invisible to a measure that counts every token type equally.
