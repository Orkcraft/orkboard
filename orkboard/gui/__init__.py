"""The face: the Board in a window or the browser, and on a paired phone, always in Office's look.

    board_host.py   Orkboard's host: the Board's commands, Stop all, updates, the first screen; `orkboard`'s main
    ideas*.py       the Board's commands (goals, ideas, plans, agents, review) on what the host gives them
    server.py       the page, the design system and one WebSocket on 127.0.0.1
    phones.py       the listener for a paired phone (pairing.py, phone_http.py, phone_tls.py, tailnet.py, pwa.py)
    static/         the page: Preact + htm + signals as ES modules, no build step (board.js; the phone's pwa/board-app.js)

This is a face: core/, realm/ and design/ never import it.
"""
