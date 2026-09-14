# Validation protocol v0: does your water flatten your coffee the way the model says?

One session = three cups, same coffee, same recipe, same day, tasted blind. About 30 minutes and one bottle of water.

## What you need

- 60 g of one coffee (any origin; note the roast level printed on the bag: light, medium or dark).
- Your normal filter brewer, grinder and scale.
- Your tap water.
- One bottled water from the reference-like list (alkalinity 25 to 60 mg/L as CaCO3): see docs/rankings.md for your country.
  Brazil examples: Dias D'Ávila, Legítima Lindóia, Cristal (Fonte Santa Bárbara), Água Mineral São Pedro.
  US examples: Crystal Geyser (Olancha or Beaughan springs), JUST Water. Europe: Volvic, Black Forest Still, Mont Blanc.
- A helper to pour the cups into three identical mugs and note which is which.
- Optional: an aquarium "KH" or alkalinity test strip (about 10 dollars for a pack) dipped in your tap water.

## Steps

1. Look up your tap water's alkalinity band in the atlas (docs/rankings.md or data/processed/atlas_v0.csv) or from your utility's report.
   Run `wac dialin --alkalinity <your value> --roast <light|medium|dark>` or read docs/task5_dialin_rules.md to get the dose change.
2. Brew cup A: tap water, your usual recipe. Record dose, water mass, grind setting, time, temperature.
3. Brew cup B: the reference bottled water, identical recipe.
4. Brew cup C: tap water, dose raised by the rule's chemistry estimate (for example +16 percent at 150 mg/L), everything else identical.
5. Helper pours A, B, C into identical mugs labelled 1, 2, 3 at random and writes down the mapping. Let them cool to the same temperature.
6. Taste and answer, for each pair (1 vs 2, 1 vs 3, 2 vs 3): which is more sour, which is more bitter, which do you prefer. Forced choice; no ties.
7. Reveal the mapping and fill in the form.

## What we record (nothing personal)

City and utility (or postcode district), roast level from the bag, roaster name (optional), filter or softener at home (yes/no/type),
recipe, dose change used for cup C, the nine pairwise answers, and the test-strip reading if you have one. No names, no street addresses.

## How the data are analysed (registered before the first submission)

Mixed-effects logistic regression: probability that the tap-water cup is chosen as the sourer one against the model's predicted acid loss
for that water, roast level as a fixed effect, taster as a random effect. Cup C versus cup B tests the compensation rule: if the rule is
right, that comparison is a coin flip. About 150 sessions across the alkalinity bands give 80 percent power for the predicted
20-percentage-point difference between the lowest and highest bands. Hard-water dark-roast sessions test the Liu 2025 hypothesis directly.

## How to submit

Open a GitHub issue with the "Brew session" template (.github/ISSUE_TEMPLATE/brew-session.yml) or send the filled form to the address in the repository README.
