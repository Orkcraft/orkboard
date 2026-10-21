# Orkboard

Orkline's Board on its own: a project's parties and their goals, the goals' specs and plans, the agents at work and the results to review, on the desktop and on a paired phone.

Install it from git: `uv tool install 'orkboard[gui] @ git+https://github.com/orkWorks/orkBoard'` (`[gui]` brings the window
elsewhere than a Mac, where it always comes, and the paired phone's TLS).

Run `orkboard` in a project's folder: it opens in a window of its own (`orkboard --browser` opens it in the browser instead),
and Open folder (Ctrl+O) opens the system's folder dialog. On a Mac, `orkboard --make-app` puts Orkboard.app in
~/Applications, to open Orkboard from the Dock, Launchpad or Spotlight on the last project.

It is drawn in [orkUI](https://github.com/orkWorks/orkUI)'s office look; on Agents each agent wears the head of its craft's race (an ork engineers, an elf designs, a goblin minds the data, a gnome markets) in its tier's gear.

It shares Orkline's settings (`~/.config/orkcraft/`) and a project's Board (`<project>/.orkcraft/`, `orkcraft.toml`): switching between the two loses nothing.
