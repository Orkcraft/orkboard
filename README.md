# Orkboard

Orkline's Board on its own: a project's goals and ideas, their specs and plans, the agents at work and the results to review, on the desktop and on a paired phone.

Install it with [orkGet](https://github.com/orkWorks/orkGet)'s installer (macOS and Linux): `curl -fsSL https://orkcraft.dev/install.sh | sh -s -- --product orkboard`, or from git: `uv tool install git+https://github.com/Orkcraft/orkboard`. `orkboard update` updates it; `orkboard usage on|off|status` is the one answer to anonymous usage stats and crash reports, for Orkline too.

Run `orkboard` in a project's folder (`orkboard --browser` opens it in the browser instead of a window).

It is drawn in [orkUI](https://github.com/orkWorks/orkUI)'s office look; on Agents each agent wears the head of its craft's race (an ork engineers, an elf designs, a goblin minds the data, a gnome markets) in its tier's gear.

It shares Orkline's settings (`~/.config/orkcraft/`) and a project's Board (`<project>/.orkcraft/`, `orkcraft.toml`): switching between the two loses nothing.
