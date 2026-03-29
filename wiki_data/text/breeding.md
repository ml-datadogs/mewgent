# Breeding

**Breeding** is a core gameplay pillar in *Mewgenics*.

## House Stats

| Name | Icon | Description |
| --- | --- | --- |
| Appeal |  | Increases the stat quality and ability diversity of new strays.  This applies to the entire house, not just to a single room.  *See Stray Cats for more info.* |
| Comfort |  | If it's **high**, it increases the odds of breeding overnight.  If it's **low**, it increases the odds of fighting overnight.  *See Breeding for more info.*  Comfort is lowered by 1 for each cat in a room above 4. |
| Stimulation |  | If it's **high**, kittens will inherit more and better things from their parents.  If it's **low**, kittens have a lower chance of inheriting anything.  *See Breeding for more info.* |
| Health |  | If it's **high**:   * Cats take longer to become old and are less likely to die of old age. * Cats have a chance of recovering from Injuries and Disorders overnight.   If it's **low**:   * Cats become old sooner. * Cats have a chance of developing [hygiene disorders](https://mewgenics.wiki.gg/wiki/Disorder_Pools#Low_Hygiene-0%7C) overnight.   *See Injuries and Disorders for more info.* |
| Mutation |  | Increases the chance for cats to develop Mutations overnight.  *See Mutations for more info.*  *Also known as Evolution (Internally)* |

## Inbreeding

Each cat has an Inbreeding coefficient (between 0-1) that is correlated to his parent's coefficient and how familiarly close they are.

It's been examined through experimentation that:

* Strays will always have coefficient of 0.
* Any breeding between relative cats, who have a **closeness** of 4 or closer, will raise that coefficient.
  + Closeness can be determined by tracing along the lines of the family tree; count how many lines separate the couple, condensing sibling relations from two lines to one:
    - 1: parent and child, siblings
    - 2: grandparent and grandchild, aunts/uncles and nieces/nephews
    - 3: great-grandparent and great-grandchild, great-aunt/great-uncle and grandniece/grandnephew, first cousins
    - 4: great-great-grandparent and great-great-grandchild, great-great-aunt/great-great-uncle and great-grandniece/great-grandnephew, first cousins *once removed*
  + The Inbreeding coefficient increases somewhat slowly. Coefficients beyond "Slightly Inbred" are typically the result of two-or-more consecutive generations of inbreeding.
* Breeding with cats who have a Closeness of 5 or higher lowers the coefficient, even if the two cats have notable Inbreeding coefficients of their own.
  + Breeding with a Stray Cat produces a kitty-cat who is **not** inbred, due to the Stray having no common ancestors with the other cat; unless the other parent is a *descendant* of the Stray, of course.

**Closeness** (C) is a variable used for finding the **Coefficient of Relatedness** (r): r=2−C.

### Math

In real life, the Coefficient of Inbreeding (*f*) of Cat *X* would be determined by the following equation:

fX=∑N0.5(n−1)⋅(1+fA)

* *N* is the number of common ancestors between both of *X's* parents
* *n* is amount of people in the familial loop connecting *X's* parents and **one** of their common ancestors (including both parents)
  + Each iteration of the sum will loop a different common ancestor
  + fA is the Coefficient of Inbreeding of the ancestor that that particular loop goes through

To simplify, the Coefficient of Inbreeding for parents **whose Coefficients of Inbreeding are zero** is half of the parents' **Coefficient of Relatedness**.

The Inbredness levels of the various icons the following:

* ≤ 0.1
* 0.10 <  ≤ 0.25
* 0.25 <  ≤ 0.50
* 0.50 <  ≤ 0.80
* 0.80 <

### Closeness Limits

In real life, a cat who manages to breed down through five consecutive generations of their own descent would continuously create increasingly-Inbred cats. In *Mewgenics*, a curious interaction with **Closeness** occurs:

* If the original breeding pair are both Strays (**Closeness** of infinity), the child will not be Inbred.
* If one of the parents breeds with the child (**Closeness** of 1), the grandchild/child will be **25%** Inbred.
* If that same parent breeds with the grandchild (**Closeness** of 2), the great-grandchild/child will be **37.5%** Inbred.
* If that same parent breeds with the great-grandchild (**Closeness** of 3), the great-great-grandchild/child will be **43.75%** Inbred.
* If that same parent breeds with the great-great-grandchild (**Closeness** of 4), the great-great-great-grandchild/child will be **46.875%** Inbred.
* If that same parent breeds with the great-great-great-grandchild (**Closeness** of 5), the great-great-great-great-grandchild/child... will ***not*** be Inbred.

This happens because **Closeness** of 5 or higher is considered negligible, while the offending Stray doesn't have *closer* relationships with their partners further down the tree.

If the player ***wants*** higher Inbredness, they have to take advantage of the fA part of the equation, by creating incestuous relationships between *two* cats who are Inbred. A twisted ladder is (in this case) preferable to a straight one.

## Kitten Birth Process

When a kitten is born, 13 steps are performed:

### 1. Furniture Effects

* **What happens**
  + All furniture effects are calculated.
* **Notes**
  + Most of these are unused, presumably due to simplified stats during development.

### 2. Inheriting Stats

* **What happens**
  + For each of the 7 core stats, one parent’s value is inherited.
* **Chance (higher stat is chosen)**
  + Probability: `(1 + 0.01 × Stimulation) / (2 + 0.01 × Stimulation)`
  + Stimulation has diminishing returns as Stimulation approaches infinity (S→∞), the probability approaches 1 but never reaches it.

| Chance | Stimulation |
| --- | --- |
| 0% | -100 |
| 10% | -89 |
| 20% | -75 |
| 30% | -57 |
| 40% | -33 |
| 50% | 0 |
| 60% | 50 |
| 70% | 133 |
| 80% | 300 |
| 90% | 800 |
| 99% | 9800 |

Chance to Succeed X Rolls Per Stimulation

| Rolls \ Stimulation | 0 | 20 | 40 | 60 | 80 | 100 | 120 | 140 | 160 | 180 | 200 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 rolls | 0.78% | 0.40% | 0.22% | 0.12% | 0.07% | 0.05% | 0.03% | 0.02% | 0.01% | 0.01% | 0.01% |
| 1 Roll | 5.47% | 3.37% | 2.14% | 1.39% | 0.93% | 0.64% | 0.45% | 0.32% | 0.23% | 0.17% | 0.13% |
| 2 Rolls | 16.41% | 12.12% | 8.97% | 6.69% | 5.04% | 3.84% | 2.96% | 2.30% | 1.81% | 1.44% | 1.15% |
| 3 Rolls | 27.34% | 24.25% | 20.94% | 17.85% | 15.13% | 12.80% | 10.85% | 9.21% | 7.85% | 6.72% | 5.77% |
| 4 Rolls | 27.34% | 29.10% | 29.32% | 28.56% | 27.23% | 25.61% | 23.86% | 22.11% | 20.41% | 18.80% | 17.30% |
| 5 Rolls | 16.41% | 20.95% | 24.63% | 27.42% | 29.41% | 30.73% | 31.50% | 31.84% | 31.84% | 31.59% | 31.15% |
| 6 Rolls | 5.47% | 8.38% | 11.49% | 14.62% | 17.65% | 20.48% | 23.10% | 25.47% | 27.59% | 29.48% | 31.15% |
| 7 Rolls | 0.78% | 1.44% | 2.30% | 3.34% | 4.54% | 5.85% | 7.26% | 8.73% | 10.25% | 11.79% | 13.35% |

### 3. Skill Share+

* **When it applies**
  + If either parent has the upgraded version,  Skill Share+    Skill Share+  Your other passive ability is shared with the other cats in your party at the start of each battle. .
* **What happens**
  + That parent’s **other passive** is guaranteed to be passed to the kitten.

### 4. Inheriting Active Abilities

* **How the parent is chosen**
  + Default: `50%` between parents
  + Bias attempt chance: `min(0.01 × Stimulation, 1)`
    - If the bias attempt triggers, and only one parent has any class abilities, the other parent’s selection chance becomes `0`.
* **What happens**
  + After a parent is chosen, one of that parent’s active abilities is selected at random.
  + If a second active ability is inherited, this parent-selection process is repeated (it is not locked to the first parent).
* **Chance**
  + First active ability: `0.20 + 0.025 × Stimulation`
  + **Guaranteed at `Stimulation ≥ 32`**
  + Second active ability: `0.02 + 0.005 × Stimulation`
  + **Guaranteed at `Stimulation ≥ 196`**

### 5. Inheriting Passive Abilities

* **How the parent is chosen**
  + Default: `50%` between parents
  + Bias attempt chance: `min(0.01 × Stimulation, 1)`
    - If the bias attempt triggers, and only one parent has any class passives, the other parent’s selection chance becomes 0.
* **What happens**
  + After a parent is chosen, one of that parent’s passives is selected at random.
  + Skill Share    Skill Share  Your other passive ability is shared with the other cats in your party at the start of each battle.  cannot be inherited.
* **Chance**
  + Probability: `0.05 + 0.01 × Stimulation`
  + At **0 Stimulation**, this is exactly `5%`
  + **Guaranteed at `Stimulation ≥ 95`**

### 6. Inheriting Disorders

* **Chance**
  + Inherit one random disorder from the mother:  `15%`
  + Inherit one random disorder from the father:  `15%`
  + These rolls are independent, meaning a kitten may inherit `0`, `1`, or `2` disorders.

* **Notes**
  + This inheritance is **not affected** by Furniture or Stimulation.

### 7. Birth-defect Disorders Roll

* **When it applies**
  + Only if fewer than 2 disorders were inherited from the parents.
* **Chance**
  + Probability: `0.02 + 0.4 × clamp(inbreeding_coefficient − 0.2, 0, 1)`
* **Notes**
  + Minimum chance is always 2% (when the condition is met).
  + Chance increases linearly once `inbreeding_coefficient > 0.2` , up to a maximum of 42%.

### 8. Birth Defects Check

* **Roll**
  + A random number is generated.
* **Condition**
  + If `random number < (inbreeding_coefficient × 1.5)` and `inbreeding_coefficient > 0.05`
* **What happens**
  + The kitten is flagged to receive birth-defect parts in step 13. Generating Birth Defects.

### 9. Body Parts

* **What happens**
  + Body parts are inherited from the parents (mutations are part variants).
* **Chance**
  + All part-sets are inherited: `80%`
  + One random part-set is **not** inherited and is instead randomly assigned `20%`; **all other part-sets are still inherited normally**.
* **How each inherited part is chosen**
  + For each inherited part, either the mother’s or father’s version is selected.
  + If only one parent’s version of that part is mutated, the mutated version is favored.
    - Probability of selecting the mutated version: `(1 + 0.01 × Stimulation) / (2 + 0.01 × Stimulation)`
    - At **0 Stimulation**, this is exactly `50%`.
  + If both parents' versions are mutated, or neither is mutated, the selection is a `50%` between parents.
* **Notes**
  + Cannot be guaranteed: as Stimulation approaches infinity (S→∞), the probability of preferring the mutated part approaches 1 but never reaches it.

### 10. Body Part Symmetrization

* **What happens**
  + For left/right parts that must match, symmetry is enforced by copying one side to the other.
    - (Leg, Arm, Eye, Eyebrow, Ear)
* **Chance**
  + Left is replaced with right: `50%`
  + Right is replaced with left: `50%`
* **Notes**
  + Maximum number of mutations on a **bred** kitten is 10 due to symmetrization.
    - (Body, Head, Tail, Leg, Arm, Eye, Eyebrow, Ear, Mouth, Fur)

### 11. Unknown

* **What happens**
  + An additional value is inherited from the parents.
* **Chance**
  + Inherited from parents: `98%`
* **How the parent is chosen**
  + Default: `50%` between parents
* **Notes**
  + The associated field/purpose is currently undocumented.

### 12. Inheriting Voice

* **What happens**
  + Voice is usually inherited from the parents, with a small chance to reroll.
* **Chance**
  + Inherited from parents: `~98%`
  + Rerolled: `~2%`
* **Notes**
  + Exact inheritance logic is not fully verified.

### 13. Generating Birth Defects

* **When it applies**
  + Only if the birth defects check in step 8. Birth Defects Check succeeded.
* **What happens**
  + Birth-defect parts are applied in one or more passes.
* **Number of passes**
  + If `inbreeding coefficient ≤ 0.9`: 1 pass
  + If `inbreeding coefficient > 0.9`: 2 passes
* **Notes**
  + Birth-defect parts are applied after normal part inheritance and may replace already-inherited parts.

## Pairing

Cats are paired for breeding attempts with the following process:
First shuffle all cats into a list, removing kittens and hungry cats. Then for each cat in the list:

1. Calculate its room's `BreedSuppression` furniture effect, i.e. whether Idol#Idol of Chastity is present. If so, skip this.
2. Otherwise choose a cat randomly, weighted by their **compatibility** (see Compatibility)
3. Once a cat is chosen, two rolls occur with probability `compatibility * Sqrt(0.1 comfort + 0.1 x)` where `x` is something to be documented.
   1. If the first roll fails, skip this cat. Its partner may still choose this cat on its turn.
   2. If the second roll fails, remove both cats from the list. No other cat can choose to breed with them that day.
   3. If both rolls succeed (with probability `compatibility2 * (0.1 comfort + 0.1 x)`), then the cats will initiate their breeding attempt. In particular, if their `compatibility > 0.05`, they will successfully have a kitten.

## Lover

Each cat can have a lover, indicated by an icon next to their name if the player has donated enough cats to Tink. This affects their `lover_coeff`, which is a hidden value between 0-1 used for calculating **compatibility** (see Compatibility). In particular, two updates are performed:

* `lover_coeff`
  + If a cat has no lover but is chosen for a breeding attempt, the other cat immediately becomes its lover and sets `lover_coeff = 1.25`. Every breeding attempt with its lover increases this by `lover_coeff → 0.9 lover_coeff + 0.1`.
    - This is essentially a weighted average pulling `lover_coeff` towards 1, albeit very slowly. In particular, its grows like 1−k(0.9)n.
  + If the cat has a lover, but was chosen in a breeding attempt not with their lover, then `lover_coeff → 0.9 lover_coeff`.

* **Rivals**
  + When cats are paired for a breeding attempt, their respective lover will change its current Rival to the other cat. This is to prevent cats from "cheating" on their current lover.
  + Every breeding attempt like this increases the rival's `hater_coeff` towards 100%.
  + This happens regardless of whether the breeding attempt was successful or rejected.
  + Rivals are more likely to start fights with each other.

## Compatibility

When two cats are paired for a breeding attempt, the game calculates their **compatibility** using the following process:

* Assign "father" and "mother" roles to the cats, with neutral gender cats filling any role. If both are the same gender, this is chosen at random.

* Checks the requirements:
  + The father and mother cannot be the same cat.
  + The father can't be a kitten (e.g. due to Eternal Youth)
  + Both parents must not be blocked from breeding.

If the above requirements are met, two values are calculated:

* `lover_mult`
  + From the mother, take its `lover_coeff` (see Lover). This is `0.25` by default.
  + If the mother has no lover, then `lover_mult = 1` (has no effect).
  + Otherwise if the father is the lover, then `lover_mult = 1+lover_coeff`
  + Otherwise, it is penalised: `lover_mult = 1-lover_coeff`

* `sexuality_mult`
  + From the mother, take its `sexuality_coeff` (see Sexuality)
  + If the parents are a male-female pair, `sexuality_mult = Cos(0.5pi * sexuality_coeff)`
  + If the parents both male or both female, `sexuality_mult = Sin(0.5pi * sexuality_coeff)`
  + Otherwise, i.e. when there is a neutral parent, this has no effect.

The final `compatibility` score is calculated as:  
`0.15 * father_charisma * mother_libido * lover_mult * sexuality_mult`

* If `compatibility < 0.05`, then the breeding attempt is rejected.
* Note that `father_charisma` is its **total**   Charisma, not base.
* As described, there is no hard-penalty for same-sex parents that are not gay. In fact, cats with `12` or more   Charisma should be successful in their breeding attempts when both cats are straight, if chosen as the father. (Needs testing)

## Age

## Gender

Each cat's gender can be either a male, female, or neutral. If a neutral cat would be chosen to be the father, they are instead assigned as the mother. This affects the Kitten Birth Process which favors the mother and father differently.

## Sexuality

Each cat has an Sexuality coefficient (between 0-1) which determines their sexuality flag.

* If `sexuality coefficient < 0.1`: Straight
* If `0.1 ≤ sexuality coefficient ≤ 0.9`: Bisexual
* If `sexuality coefficient > 0.9`: Gay

* **Stat Distribution**
  + Sexuality (gayness) is evenly distributed, with:
    - `81.9%` chance of being Straight.
    - `07.2%` chance of being Bisexual.
    - `10.9%` chance of being Gay.

* + The true sexuality coefficient is uniformly random with the same bounds above.

## Libido

Each cat has an Libido coefficient (between 0-1) which determines their libido level.

* If `libido coefficient < 0.3`: Low libido
* If `0.3 ≤ libido coefficient ≤ 0.7`: Mid libido
* If `libido coefficient > 0.7`: High libido

* **Stat Distribution**
  + Libido is calculated by taking the larger of four random numbers between `0` and `0.5`. There is a further 50% chance to flip it above `0.5`, so that lower libido appears as often as higher libido. Mathematically, Libido=M or 1−M,M=max⁡(U1,U2,U3,U4),Ui∼Uniform[0,0.5]

| Top % of cats | Libido ≥ |
| --- | --- |
| 50% | 0.500 |
| 25% | 0.580 |
| 10% | 0.666 |
| 6.5% | 0.7 (High) |
| 5% | 0.719 |
| 2% | 0.776 |
| 1% | 0.812 |
| 0.1% | 0.894 |

## Aggression

Each cat has an Aggression coefficient (between 0-1) which determines their aggression level.

* If `aggression < 0.3`: Low aggro
* If `0.3 ≤ aggression ≤ 0.7`: Mid aggro
* If `aggression > 0.7`: High aggro

* **Stat Distribution**
  + Aggression is uniformly distributed from 0-1.

## Fertility

Each cat has a hidden Fertility coefficient (between 1.0-1.25) which controls the probability of having twins on a successful breeding attempt. Each parent contributes their own fertility value, which are multiplied together to get a final `combined_fertility`.

* If `combined_fertility > 1`: 1 kitten is guaranteed, and there is a `0% < combined_fertility-1 < 56.25%` chance of the pair having twins.

* **Stat Distribution**
  + Fertility is calculated by taking the smaller of two random numbers between `1` and `1.25`. Mathematically, Fertility=min⁡(U1,U2),U1,U2∼Uniform[1,1.25]
  + The average fertility of a cat can be calculated to `1.0833`. This means the average probability of a random breeding attempt yielding twins is `17.36%`.

| Top % of cats | Fertility ≥ |
| --- | --- |
| 50% | 1.0732 |
| 25% | 1.125 |
| 10% | 1.171 |
| 5% | 1.194 |
| 2% | 1.214 |
| 1% | 1.224 |
| 0.1% | 1.242 |

## References

* <https://gist.github.com/SciresM/95a9dbba22937420e75d4da617af1397>