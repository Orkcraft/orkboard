# orkUI / office

Dark, monochrome, dense. **Colour is a signal** (danger, alert, success), except the one ork green of the primary action
and the muted heads of the races.
The **pixel face** (Pixelify Sans) is for buttons and headings only, never below 12 px, whole pixels, no ligatures, no faux
bold, never for a number or a person's text; **everything else is IBM Plex Mono** (12/18 on the desktop, 16/22 on the phone).
Nothing is round: edges 1 px, corners notched by 2 px (`clip-path` on a control's `::before`, so the hit area is whole),
dialogs framed `3px double`. Selected is raised with a 2 px ink bar, never a white box. Every arrow and icon is a pixel mark.

## The ork legend (a one-character mark never stands alone: its word is beside it)
`@` Taskmaster · `o` Grunt · `?` idea · `*` goal · `+` task

## Where each ork stands
`ork.txt` an empty screen · `ork-asleep.txt` the work waits for the night · `ork-asks.txt` the first thing on the list is a
question · `ork-failed.txt` the only content is a failure · `ork-working.txt` an ork is working and there is nothing to read.
On an empty screen the ork and its sentence are one block, centred on both axes in the pane's free area.

## The races
`races/` holds the six races in three tiers (generated; `../races/README.md`): 24 x 22 beside a word in a row, 48 x 44 @2x.
They are the only raster art of the look, in colour but muted: no head is more colourful than a signal, and a state goes
beside the head in its signal colour, never onto it.
`.ork-race` puts a head beside its word: `<span class="ork-race"><img class="ork-race__head" src="races/elf-elder.png"
srcset="races/elf-elder@2x.png 2x" alt=""><span class="ork-race__word">… <span class="ork-race__tier">…</span></span></span>`, 24 x 22
in a row, `.ork-race.big` 48 x 44.

Pointer targets are at least 24 x 24 px; on the phone a control is 40 px drawn and 44 px to hit (`min-height: var(--ork-tap)`).
