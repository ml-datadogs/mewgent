# Stats

Stats affect everything your cat does, and can be increased throughout a cat's life. for the purposes of breeding, only the stats a cat started with can be passed down onto their children, with the room's Stimulation statistic determining whether the higher stat or the lower stat is inherited. Stray cats arriving at the house have their stats determined by the Appeal statistic, with higher Appeal giving them better stats.

## Combat Stats

| Stat Name | Short Form | Icon | Explanation |
| --- | --- | --- | --- |
| Strength | STR |  | Determines how much damage your cat will deal with *melee* attacks and abilities. These abilities are usually indicated with a  Melee icon. 5 Strength is neutral. Every additional point adds 1 to melee damage for *most* attacks/abilities, and vice-versa. Some abilities scale at half the rate like **Dexterity**  Affects the Strength option in events (e.g. pulling out something's eye, opening a rusted toilet). |
| Dexterity | DEX |  | Determines how much damage your cat will deal with *ranged* attacks and abilities. These abilities are usually indicated with a  Ranged icon. 5 Dexterity is neutral. Every 2 additional points equals 1 to ranged damage for *most* attacks/abilities, and vice-versa.  Affects the Dexterity option in events (e.g. avoiding a mouse trap, climbing a fence). |
| Constitution | CON |  | Determines Max HP and post-combat regeneration. HPmax=CON⋅4, with the lowest possible value being 1 at 0 CON or lower. Affects the Constitution option in events (e.g. surviving poison, eating a really big poop). |
| Intelligence | INT |  | How much mana you can regenerate at the end of your turn. Negative intelligence cannot cause mana to deplete over time, but will have other effects. Affects the Intelligence option in events (e.g. reading a book, solving a puzzle box). If a cat has 0 intelligence or less, the event text gets transformed into cavespeak. |
| Speed | SPD |  | How many tiles you can move on a turn, as well as when you will take your turn in turn order. Affects the Speed option in events (e.g. running from something and... running from something else!). |
| Charisma | CHA |  | How much max mana you can have, how much mana you start each combat with, and how skilled you are at breeding. Maximum mana is calculated as Manamax=CHA⋅3. Affects the Charisma option in events (e.g. charming a monster, being really good in bed). |
| Luck | LCK |  | The primary modifier to much of the randomness within Mewgenics, as well the main determinant behind an attack’s critical hit chance. All displayed odds in the game assume a neutral luck stat of 5. Each point away from the baseline adds a **10% chance** for the game to roll an extra die when it calculates for an outcome. Extra rolls from high luck take the **best** result of what was rolled for that outcome, and low luck takes the **worst**. Additional dice stack at higher magnitudes (i.e. +1 roll at -5 and 15 luck, +2 at -15 and 25, etc).  The base critical hit chance with 5 luck is **10%**, and each additional point of luck adds **2%** to crit chance before extra rolls are applied.  Affects quality of items in shops and post-battle rewards.  Affects the Luck option in events (e.g. surviving an impossible battle, winning the lottery). Also affects the outcome of events even if luck is not directly tested.  For a cat with   Luck L, the chance of success S is given by the following formula:  S={L≥5:1−fn(1−as)L<5:sn(1−af)  where:   * s is the base probability of success before   Luck is factored in. * f=1−s. * a=k−⌊k⌋, where k=|L−510|. * n=1+⌊k⌋. |

Each of a cat's **base stats** will be between **3** and **7**. A stray cat with a 3 or 7 stat will be less common if the House has low Appeal.

A stat of 5 is considered the baseline for most skill checks, with a 50/50 chance of a good or bad outcome. There is a separate base 15% chance of getting a more extreme result.

* There may be other factors at play (i.e. **Luck** or Difficulty). See Events § Probabilities for more information.

### Derived Stats

| Stat Name | Short Form | Icon | Explanation |
| --- | --- | --- | --- |
| Health | HP |  | Health is a measure of how much damage a unit or object can receive until it is **downed** or **destroyed**.  * When unit drops to 0% of their maximum Health, they are usually **downed** (or otherwise defeated). In most cases, this causes them to lose their turn and lose all Status Effects (besides Rot). A downed unit cannot regain Health from healing (nor Shield and Holy Shield) unless **revived**. * Health is replaced by **Corpse Health** on downed units. * There are certain exceptions to a unit or object being **downed**:   + Many Objects, Enemies and some Familiars have 0 **Corpse Health** and are **destroyed** (or activate their unique on-death ability) upon being reduced to 0% health.   + Downing a non-allied cat with a hit that reduces them to -100% of their maximum health causes them to be **destroyed**.   + Certain abilities and items (i.e.  Daddy Shark's   Daddy Shark's  Will instantly kill anything it can reach! Gains bonus turns for each bleeding unit. Focuses on bleeding units.  attack and  Throbbing Gristle   Throbbing Gristle (Weapon)  Take it to the Wall of Flesh in the Caves. All units die when they get downed. Use: A melee attack that turns things it kills into Meat. ) can cause the unit to be **destroyed**, sometimes bypassing Health entirely.   + Downing a unit that is Infested causes them to be **destroyed** (and spawns a unit responsible for the infestation in its place).   Battles end when all enemy units are **downed** or **destroyed**. When this happens, allied cats will typically be revived and Heal for an amount of HP equal to their   Constitution; but certain factors can reduce it by one or two points or even nullify it.  Outside of battle, cats' Health can never be lower than 1. Outside of specific events that kill cats, if an Event would reduce a cat's Health to zero, it is reduced to 1 instead. |
| Mana | MP |  | Mana is required for using most active abilities, known in-game as **spells**. It is never necessary for any unit's primary action, known as their **basic attack** or **basic action**. Cats start each battle with an amount of Mana equal to their   Charisma. At the end of each turn, they gain an amount equal to their   Intelligence.  Downed cats **still have and gain Mana**; but most of them don't have abilities that can be used while downed, so they skip their turns automatically. |

### Others

| Stat Name | Short Form | Icon | Explanation |
| --- | --- | --- | --- |
| Shield | SH |  | **Shield** functions as **temporary   Health** attached to the front of one's "health bar". Unused Shield goes away at the end of each battle. Most damage affects **Shield** before Health, allowing it block damage that would otherwise transition between fights.  Notable exceptions are:   * Bleed * Poison   Any passive effect that provides Shield does so at the start of each battle. |
| Holy Shield | HS |  | **Holy Shield** functions as protection against hits, **blocking** full instances of damage. Unused Holy Shields go away at the end of each battle. Attacks that bypass Shield also bypass Holy Shield.  Any passive effect that provides Holy Shield does so at the start of each battle. |
| Corpse Health |  |  | **Corpse Health** also known as **Corpse HP**, is the amount of **hits** a downed unit takes before being **destroyed** and killed *permanently*. Each instance of added healing, Shield or Holy Shield increases Corpse Health by 1, regardless of amount of healing.  Allied cats have a base value of 3, while enemies can range from 0 to 5.  Starting with 0 or less Corpse Health means your body will be destroyed **immediately**, often referred to as not leaving a body. |
| Level Up Reroll |  |  | **Level Up Rerolls** allow you to reroll your level up options, regardless of Stats, Passives or Active abilities. |

Units still require   Health (at least more than 0% of their max HP) to avoid death or being downed. This is relevant because Poison, Bleed, Burn, and certain attacks **bypass both types of Shields**.

## In-House Stats

### Room Stats

* Stats affected by Furniture, Overcrowding & Dead Bodies.

| Name | Icon | Description |
| --- | --- | --- |
| Appeal |  | Increases the stat quality and ability diversity of new strays.  This applies to the entire house, not just to a single room.  *See Stray Cats for more info.* |
| Comfort |  | If it's **high**, it increases the odds of breeding overnight.  If it's **low**, it increases the odds of fighting overnight.  *See Breeding for more info.*  Comfort is lowered by 1 for each cat in a room above 4. |
| Stimulation |  | If it's **high**, kittens will inherit more and better things from their parents.  If it's **low**, kittens have a lower chance of inheriting anything.  *See Breeding for more info.* |
| Health |  | If it's **high**:   * Cats take longer to become old and are less likely to die of old age. * Cats have a chance of recovering from Injuries and Disorders overnight.   If it's **low**:   * Cats become old sooner. * Cats have a chance of developing [hygiene disorders](https://mewgenics.wiki.gg/wiki/Disorder_Pools#Low_Hygiene-0%7C) overnight.   *See Injuries and Disorders for more info.* |
| Mutation |  | Increases the chance for cats to develop Mutations overnight.  *See Mutations for more info.*  *Also known as Evolution (Internally)* |

### Breeding & Living

The following are primarily important in the House & Breeding section of the game.

| Stat | | Explanation |
| --- | --- | --- |
| Age | | Each new in-game Day, all cats you have age by **1**. All Strays encountered, start at an age of 2.  Cats with a age of 1, are **Kittens**.  Cats starting at age 2, are adults and can be used for Breeding, Fighting other cats, Adventures, defending against House Bosses.  Cats starting at age 5, can be sent to Tracy.  Cats starting at age 21, have a small chance to become **Old** as an overnight event.  A low Health stat can make cats become old sooner, while high Health increases their life span on average.  Cats can have their age reverted to 1 by the Fountain event, the  Eternal Youth disorder, or by having their corpse destroyed with  Cat Rib   Cat Rib (Trinket)  When your body is destroyed, you are reborn as a kitten!  equipped.  This does **Not** revert their "Time until Old" internal value.  Cats with  Eternal Youth cannot age. |
| Kitten |  | Cats with an Age of 1 are Kittens. Kittens cannot be used to go on Adventures or defend against House Bosses.  Kittens can be sent to Tink.  Kittens become Adults if their age is increased to 2, which usually happens after 1 in-game day.  Kittens have **-2** to each stat while they are on adventures, **cannot** level up, and will not become Retired upon returning home. |
| Old |  | An old cats age can vary a lot depending on which room they lived in and player luck. Old cats also have a small chance to **die of old age** as an overnight event, which can potentially happen on the same night they get Old.  Old cats become Exhausted starting at Round **5**, instead of Round 10.  This *can* be beneficial due to Adrenaline |
| Hunger |  | When passing the day, each cat will consume 1 unit of food, unless the cat is Vegan, has the "No Mouth" or "Bandage Mouth" mutation. If the player has less food available than there are cats, some of the cats have a chance to starve and die. Hungry cats suffer -1 to all stats until they are fed. |
| Retired |  | Cats become Retired upon finishing an Adventure, as long as they did not turn into a Kitten during it.  Retired cats cannot be used to go onto another adventure, and can be sent to Frank.  Depending on the adventure, Butch will also accept them.  Retired Cats wear a Crown, with the size depending Chapter and color on Act beaten.     Cats become "Super Retired" upon defeating a House Boss, regardless of if they were "regular" retired.  Super Retired cats cannot be used for another House Boss or adventure, and gain a red flame effect over their crown. |
| Sex Gender |  | Gender determines which cats a cat can and wants to breed with, and whether or not it can produce offspring in that breeding interaction. **Neutral Gender**, can produce offspring with both Male and Female cats.  Only 10% of Cats are born as **Neutral Gender**.  (? Gender is referred to as Neutral in files & has been referred to as Non-Binary & Ditto Gender by the developers, but wording has been inconsistent) |
| Inbredness | (Normal)   (>10%)   (>25%)   (>50%)   (>80%) | When a cat is born, their Inbredness determines if they develop **new Birth Defects**.  * A cat has to be *at least* 5% Inbred to develop "typical" Birth Defects, new "cat parts" with mostly-negative effects.   + The Inbredness indicators are not very helpful here; even 6.25% Inbredness is marked as  **"Not Inbred"**. * All cats have a base 2% chance to be born with new Birth-Defect-Disorders, such as  Autism; however, the chance jumps to 10% for cats who are 20% Inbred, and additional Inbredness increases the likelihood at a 1:0.4 ratio.   + Inbredness indicators are more helpful here; 28% Inbredness is marked as  **Moderately** Inbred, for example.   As a stat, it functions similarly to the [inbreeding coefficient](https://en.wikipedia.org/wiki/Coefficient_of_inbreeding) (COI, or just "F"). Inbreeding between **relatives** compounds on both parents' Inbredness scores. Strays are automatically assumed to be **completely unrelated** to other cats, and thus always have kittens who are  **Not** Inbred.  Inbredness indicators are unlocked by getting Mr. Tinkles to Favor level 3.  This comes with a Family Tree option, which indicates that the game only tracks a cat's **five previous generations**. According to the Breeding article, relationships further apart than that of first cousins (or a great-great-grandparent and their great-great-grandchild) are too distant to notably increase Inbredness, and may even reduce it. |
| Libido | (>70%)   (Normal)   (<30%) | Libido primarily impacts the chance for a cat to **initiate** breeding, and secondarily impacts the chance for a cat to **accept** breeding. While Comfort is very important for whether or not breeding will occur in a room, Libido acts like a weight system, determining **who** will initiate that breeding. (The initiator's   Charisma and the target's Gayness presumably play bigger roles in whether or not the target will oblige.)  Typically, **males will initiate with females**. In pairings with ?-sex (or "Ditto-gender") cats, either one is equally likely to be the initiator.  Libido indicators are unlocked by getting Mr. Tinkles to Favor level 4. |
| Gayness | (>90%)    (>=10%) | A cat's Gayness is a number between 0 and 1, determining whether or not they will **initiate and/or accept** same-sex intercourse. To break it down:   * Gayness is the ratio of whether-or-not a cat will initiate breeding with a cat that **isn't** the opposite sex. * If the initiator is of the **same** sex as the targeted cat, the targeted cat's Gayness partially determines whether-or-not they will **accept** it. * If the initiator is the **opposite** sex of the targeted cat, the targeted cat's Gayness partially determines whether-or-not they will **reject** it.   It may at first seem like whether-or-not a cat accepts same-sex intercourse doesn't matter. However, many cats develop "favored partners", so a cat who does same-sex intercourse is less likely to do opposite-sex intercourse later.  Neutral Gender cats are technically **not** the opposite of either regular sex, nor are they the same as either of them. They also ignore their own Gayness if they are the **targeted** cat, though not if they are the initiator.  [Pride flags](https://en.wikipedia.org/wiki/Pride_flag) as indicators. **Rainbow flag** means the cat is gay and will only look for same-sex intercourse and **pink and blue flag** means they're bisexual and can possibly mate with either sex.-->  The "Gaydar" (Gayness indicator) is unlocked by getting Mr. Tinkles to Favor level 4. |
| Aggression | (<30%)   (Normal)   (>70%) | Aggression primarily impacts the chance for a cat to **initiate** cat-fights, as well as how **violent** a cat-fight they are in may be. While Comfort is very important for whether or not fighting will occur in a room, Aggression acts like a weight system, determining **who** will initiate that fighting.  More research has to be done on what impacts the results of a fight. However, it appears that a cat's Aggression increases the likelihood of their opponent **dying**, if they win the fight.  Aggression indicator is unlocked by getting Mr. Tinkles to Favor level 6. |
| Relationships | | Cats can form **one** "love" relationship, and **one** "hate" relationship.   * If a cat is chosen to breed, they will try to breed with the cat they **love**. * If a cat is chosen to fight, they will try to fight with the cat they **hate**.   Relationship indicators are unlocked by getting Mr. Tinkles to Favor level 7. |

## Injuries

Injuries are permanent stat decreases applied to a cat whenever they are downed or from other unique events such as Cat Fights in the House. Some effects can also heal injuries, provide immunity to some or all injuries, force all injuries to convert to a specific type, or trigger unique bonuses based on possessed injuries.

### Basic Injuries

These injuries are applied by any event that chooses a "random" injury, such as death, but can also be chosen non-randomly from certain events.

| Icon | Name | Stats | Notes |
| --- | --- | --- | --- |
|  | Broken Paw | -1  Strength | Inflicted by  Paw Breaker    Paw Breaker  A huge punch that breaks your paw... (You get -1   permanently.) |
|  | Torn Tendon | -1  Dexterity |  |
|  | Broken Rib | -1  Constitution |  |
|  | Concussion | -1  Intelligence | Replaces all injuries on cats with the  Thick Skull    Thick Skull  All injuries you get are Concussions. You get +3 Shield for each concussion you have. This caps at 30 Shield.  passive. Inflicted by  Lord Bunga   Lord Bunga  Retaliates when hit. Consumes adjacent units at the start of his turn. Blind to units behind him. |
|  | Disfigured | -1  Charisma | Replaces all injuries on cats with the  Mad Visage    Mad Visage  All injuries you get are Disfigured. While at full mana, your basic action inflicts Madness. While you have 0 or less CHARISMA you can attack an additional time each turn.  passive. |
|  | Broken Leg | -1  Speed | Replaces all injuries on cats with the  My Leg!    My Leg!  All injuries you get are Broken Legs. If you have four broken legs, gain +4 Thorns, Trample, and adjacent allies have Toss as a bonus ability.  passive. |
|  | Jinxed | -1  Luck | Replaces all injuries on cats with the  Eternal Health    Eternal Health  Suffer only Jinxed when downed. When your party wins a battle, if you were downed, heal to full.  passive. |

### Special Injuries

These injuries can only be obtained from specific events, and not as a "random" injury.

| Icon | Name | Stats | Notes |
| --- | --- | --- | --- |
|  | Immolated | -1  Charisma -1  Luck | Obtained by being downed by Burn damage. |
|  | Exsanguinated | -1  Strength -1  Dexterity | Obtained by being downed by Bleed damage. |
|  | Poisoned | -1  Constitution -1  Intelligence | Obtained by being downed by Poison damage. |
|  | Cursed | -2  Luck | Sometimes inflicted by certain events. |
|  | Radiated | -1  Constitution | Sometimes inflicted by the Elephant's Foot event. |

* **Fade**, appears like a injury on certain shade copies. This is just a purely cosmetic effect.

### Unimplemented Injuries

These injuries are referred to as "todo" injuries in data comments, but do not actually exist yet as distinct injuries. They may be added in later.

| Name | Stats | Notes |
| --- | --- | --- |
| **Cracked Tooth** | -1 melee damage | Instead just gives -1  Strength, but not as the "Broken Paw" injury |
| **Broken Jaw** | -1 damage   Can't eat food | Instead just gives the "Disfigured" injury |