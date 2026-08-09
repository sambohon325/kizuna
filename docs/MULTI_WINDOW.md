# Multi-window workspaces

Every craft dashboard includes **Open in new window**. The new window keeps the currently selected production and removes the main navigation rail and milestone tracker, leaving a focused workspace for a second monitor.

Supported workspaces include AI Crew, Style Lab, Writer's Room, Character Studio, Worlds, Shots, Timeline, Audio, Composite, and Render Farm. Opening the same workspace and production again reuses its named window when the browser supports that behavior.

Workspace URLs can also be bookmarked:

```text
/?workspace=characters&project=1&popout=1
```

The `workspace` value can be `crew`, `style`, `writer`, `characters`, `worlds`, `shots`, `timeline`, `audio`, `compositor`, or `render`. Browsers may require pop-ups to be allowed for the Kizuna server before they create a separate window instead of a tab.
