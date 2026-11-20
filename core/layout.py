"""layout.py: Video compositor layouts for 9:16 vertical short-form content.
Includes Stacked Gaming Layout (Facecam on top + Gameplay below), Fill with dynamic zoom, and Fit-Blur.
"""

def build_filter_graph(layout_mode: str, dur: float, ass_filename: str, focus: float = 0.5, facecam_pos: str = "bottom-left") -> str:
    """
    Construct the FFmpeg -filter_complex string for 1080x1920 vertical canvas.
    """
    ass_filter = f",ass={ass_filename}" if ass_filename else ""

    if layout_mode == "stacked":
        # Facecam (top 720px) + Gameplay (bottom 1200px) = 1920px height
        # Map facecam position coordinates in standard 16:9 frame (1920x1080 or 1280x720)
        if facecam_pos == "top-left":
            fc_crop = "crop=w=iw*0.35:h=ih*0.45:x=0:y=0"
        elif facecam_pos == "top-right":
            fc_crop = "crop=w=iw*0.35:h=ih*0.45:x=iw*0.65:y=0"
        elif facecam_pos == "bottom-right":
            fc_crop = "crop=w=iw*0.35:h=ih*0.45:x=iw*0.65:y=ih*0.55"
        else: # default bottom-left
            fc_crop = "crop=w=iw*0.35:h=ih*0.45:x=0:y=ih*0.55"

        # Gameplay crop focuses on center action
        gp_crop = "crop=w=iw*0.70:h=ih:x=(iw-ow)/2:y=0"

        vf = (
            f"[0:v]fps=30,split=2[in_fc][in_gp];"
            f"[in_fc]{fc_crop},scale=1080:720:force_original_aspect_ratio=increase,crop=1080:720,setsar=1[top];"
            f"[in_gp]{gp_crop},scale=1080:1200:force_original_aspect_ratio=increase,crop=1080:1200,setsar=1[bottom];"
            f"[top][bottom]vstack=inputs=2{ass_filter}[v]"
        )
        return vf

    elif layout_mode == "fit":
        # Whole 16:9 frame over a blurred background
        vf = (
            f"[0:v]fps=30,split[bg_in][fg_in];"
            f"[bg_in]scale=-2:1920,crop=1080:1920,boxblur=24:2,eq=brightness=-0.25[bg];"
            f"[fg_in]scale=1080:-2[fg];"
            f"[bg][fg]overlay=0:(H-h)/2{ass_filter}[v]"
        )
        return vf

    else:
        # Default: "fill" with 9:16 crop and slow push-in zoom
        safe_dur = max(dur, 1.0)
        # Scale so height is well above 1920 to allow zoom headroom, then
        # apply a slow push-in zoom by increasing scale over time and cropping
        # to 1080x1920. The focus parameter controls horizontal position.
        vf = (
            f"[0:v]fps=30,"
            f"scale=w=-2:h='2*trunc(960*(1+0.08*t/{safe_dur:.2f}))':eval=frame,"
            f"crop=1080:1920:(iw-1080)*{focus}:(ih-1920)/2"
            f"{ass_filter}[v]"
        )
        return vf
