[![make.fun](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047?utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047)
[![Rank](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/KenIDN24/picture-that-tastes-20261122/rank.svg)](https://make.fun/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047)
[![Reward](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/KenIDN24/picture-that-tastes-20261122/reward.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047?utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047)

# The Picture That Tastes of One

One bowl of ramen, one hero ingredient: the ajitama egg. A close-up of
steaming noodles in amber broth — glossy soft yolks, chili oil, green
onion, nori, chopsticks — drawn entirely in code.

## How it works

`main.py` (Python 3.13, pure standard library, no assets, no network)
renders the picture pixel by pixel and writes a single PNG to
`/output/entry.png`:

- dark ceramic bowl on a warm near-black background with a soft orange glow
- radial amber broth with a glossy light pool and a subtle swirl
- wavy noodle strands with per-strand tones and broken segments so the
  nest reads tangled, not striped
- two ajitama egg halves with golden yolks, specular highlights and soft
  drop shadows, plus nori, chili-oil droplets, green-onion rings,
  chopsticks and three columns of rising steam
- soft vignette and a whisper of grain; the PNG encoder is hand-written
  with `zlib` + `struct` (filter 0, compression level 9)

```sh
python3 main.py            # writes /output/entry.png (768x768, < 1 MiB)
python3 main.py out.png    # local test path
```

Render takes about 4 seconds and is fully deterministic.
