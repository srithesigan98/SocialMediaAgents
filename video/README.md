# Remotion video

<p align="center">
  <a href="https://github.com/remotion-dev/logo">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://github.com/remotion-dev/logo/raw/main/animated-logo-banner-dark.apng">
      <img alt="Animated Remotion Logo" src="https://github.com/remotion-dev/logo/raw/main/animated-logo-banner-light.gif">
    </picture>
  </a>
</p>

Welcome to your Remotion project!

Scaffolded with `npx create-video@latest --yes --blank`. The matching Claude
Code Agent Skills (from
[remotion-dev/skills](https://github.com/remotion-dev/skills)) are vendored
in the repo root at `.claude/skills/remotion-*` and `.claude/skills/mediabunny`,
alongside this project's own skills — use `/remotion-create` and friends when
building compositions here.

`remotion.config.ts` auto-detects the headless Chrome shipped in Claude Code
web/remote sessions (network egress there can't reach Remotion's own browser
download) and falls back to Remotion's default elsewhere, so `npx remotion
render` works unmodified in both environments.

## Commands

**Install Dependencies**

```console
npm i
```

**Start Preview**

```console
npm run dev
```

**Render video**

```console
npx remotion render
```

**Upgrade Remotion**

```console
npx remotion upgrade
```

## Docs

Get started with Remotion by reading the [fundamentals page](https://www.remotion.dev/docs/the-fundamentals).

## Help

We provide help on our [Discord server](https://discord.gg/6VzzNDwUwV).

## Issues

Found an issue with Remotion? [File an issue here](https://github.com/remotion-dev/remotion/issues/new).

## License

Note that for some entities a company license is needed. [Read the terms here](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md).
