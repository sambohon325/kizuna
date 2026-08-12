# Kizuna interface system

Kizuna uses one shared interface foundation across every creative department. Craft workspaces may differ in layout, but controls, typography, hierarchy, navigation, and feedback must remain predictable.

## Progressive disclosure

- **Beginner** is the default. Show the active craft, one clear next action, and only the controls needed to complete it. Longer walkthroughs, craft guidance, agent configuration, and specialist settings stay available behind plainly named expansion controls.
- **Intermediate** exposes the complete craft sequence, supporting context, and commonly adjusted controls.
- **Advanced** exposes the full production toolset in a denser layout for experienced operators.
- Experience level changes presentation only. It must never change saved production data, compliance gates, approvals, AI autonomy, output quality, or available capabilities.
- AI autonomy is a separate choice. A beginner may work manually, and an advanced user may delegate heavily.

## Baseline

- Body copy is 16px with a comfortable line height.
- Supporting copy is 14px and labels are at least 13px.
- Metadata never drops below 12px.
- Standard controls are at least 44px high.
- Each screen has one visually dominant primary action.
- Advanced settings use progressive disclosure.
- Empty states explain the missing prerequisite and lead to its resolution.
- Full-width creative canvases use available screen space.

## Shared workspace anatomy

1. Production context and factual milestone status
2. Craft eyebrow, title, and short outcome-focused introduction
3. Project selection and primary action
4. Navigator or asset browser
5. Main creative canvas
6. Contextual inspector or AI collaborator

## Home command center

- Home remembers the production most recently opened in a craft workspace.
- The hero keeps Kizuna's creative identity on the left and shows the active production, factual milestone count, release scope, and next saved step on the right.
- Every production card states its own next real milestone and offers **Continue**. Decorative workflow lights never imply completion.
- Selecting a different production updates Home, Right now, and the production flow without changing that production's saved work.

## Production chapters and environment

- Global navigation is horizontal and grouped into **Home**, **Imagine**, **Direct**, **Finish**, and **Studio**. The first row selects a chapter; the second row contains only that chapter's workspaces.
- The global navigation must never require vertical scrolling. On narrow screens, all five chapter names remain visible and only the contextual tool row may scroll horizontally.
- The environment changes subtly as the production story advances: cool indigo for story, violet/teal for design, warm amber/blue for motion, magenta/indigo for sound, cyan for finishing, green for mastering, and quiet slate for studio operations.
- Chapter color is atmospheric context, not a status signal. Completion, warnings, compliance, and approvals retain their factual semantic colors.
- Workspace surfaces, typography, controls, and content contrast do not change between chapters; only the low-contrast page backdrop and navigation accents shift.

## Visual-development workspaces

- In Beginner, **AI Crew** begins with four plain-language working relationships. Customizing a creative partner is a three-step conversation: choose a craft, shape its name/personality/supervision, then save it. Provider routing, model overrides, and tool permissions appear in Intermediate and Advanced.
- In Beginner, **Style Lab** begins with the audience's emotional experience and originality guardrails beside a live creative-DNA board. Technique vocabulary and the full six-stage sequence appear when the creator moves to Intermediate.
- In Beginner, **Character Studio** and **Worlds & Backgrounds** place the visual card library across the top, the active craft canvas beneath it, and a focused AI creative partner beside the work. This makes choosing or creating an asset the obvious first action.
- Character and world stages remain available as plain-language tabs so a creator can move between story, design, model, staging, lighting, and assets without losing context.
- Intermediate and Advanced restore the denser three-column library/canvas/inspector layout. Changing levels never discards field values or changes the selected stage.
- Visual libraries scroll horizontally in Beginner and return to compact grids in deeper modes.

## Directing and editing workspaces

- In Beginner, **Storyboard & Shot Planner** presents scenes as a horizontal story shelf, the active shot board as the main canvas, and a focused **Story & action** inspector beside it. Camera, continuity, and batch-coverage controls return in Intermediate and Advanced.
- In Beginner, **Timeline & Animatic** presents source clips as a horizontal media shelf, then keeps the program monitor, quick clip timing, and magnetic sequence in a clear top-to-bottom flow. Detailed edit tools, transition timing, and advanced export controls return in deeper modes.
- Switching back to Beginner restores the primary inspector for each craft without changing a shot, clip, approval, or saved production decision.
- Horizontal shelves hide their browser scrollbars while remaining scrollable by wheel, trackpad, touch, and keyboard focus.

## Sound and finishing workspaces

- In Beginner, **Audio & Voice Studio** keeps the multitrack arrangement central and names its three supporting tasks plainly: **Edit selected sound**, **Create sound**, and **Voice & rights**. Precision split, duplicate, delete, snap, and zoom controls return in Intermediate and Advanced.
- With no audio region selected, Beginner opens **Create sound** with the AI Sound Producer. Selecting a region opens its focused editor; switching experience levels never changes the arrangement.
- In Beginner, **Scene Compositor** presents the finishing queue as a horizontal shot shelf above the picture canvas. The inspector offers **Layers** and **AI Animator**, while Camera & Grade returns in deeper modes.
- Selected-layer properties begin collapsed in Beginner so the picture and layer stack remain the primary decisions. They can still be expanded without changing experience level.

## Delivery and render workspaces

- **Timeline & Animatic** always exposes a two-step delivery path: create a lightweight review copy, then export the final video. Beginner mode must never hide the ability to finish a production.
- Quality choices use audience-facing names such as **Full HD** and **Ultra HD**. Segmented Hive export remains available as an expandable option for long or distributed renders.
- In Beginner, **Render & Hive** answers three questions first: whether the studio is ready, what is rendering, and what needs attention. Slot counts, worker services, schedules, throttles, and task routing remain available in deeper views.
- Switching to Beginner returns Render & Hive to **Status** without stopping, reassigning, or changing any active job.

## Studio operations

- **Asset Library** begins as a visual shelf: browse, select, approve, and use. Metadata and version management appear in Intermediate and Advanced modes.
- **Production Activity** begins with work that is active or needs attention. Queue names, worker details, and event history remain available at deeper levels.
- **Settings** uses six stable Beginner destinations in creator language: Workspace, AI & tools, Computers & costs, Storage & backups, Team & access, and Identity & rights. Server Operations appears in Intermediate and Advanced.

## Interaction hierarchy

- Primary: the next meaningful creative or production action
- Secondary: safe supporting operations
- Quiet: optional settings, view changes, and navigation
- Destructive: removal, rejection, revocation, or deletion

The system must remain recognizable to professional creators without requiring prior knowledge of Kizuna's database or internal pipeline.
