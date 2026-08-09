# Picture and audio editing

## Picture timeline

The Timeline is a horizontal magnetic sequence. Drag a clip onto another clip to change its position; Kizuna persists the complete order in one validated update. Use the zoom control to change clip-card width without changing timing. The inspector remains the precise place to set duration and transitions.

## Audio arrangement

Audio uses four standard lanes: dialogue, music, sound effects, and ambience. Regions can be selected, dragged horizontally, and resized from their right edge. The Snap menu controls the time increment used by those edits. Click empty lane space or enter a time to position the red playhead.

- **Split** cuts the selected region at the playhead when it falls inside the region, or at its midpoint otherwise. For local audio, Kizuna creates two new WAV files and retains the original source.
- **Duplicate** creates another editable region offset by the current snap value. The media file is shared and not copied unnecessarily.
- **Delete** removes the selected region from the arrangement without deleting its underlying media file.

Every structural audio edit marks the Timeline draft so the creator knows the previous mix should be rendered again. Region updates continue to feed proxy animatics and production masters through the existing mix pipeline.
