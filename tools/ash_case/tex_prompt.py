import json, urllib.request
P = {}
P["1"] = {"class_type": "Trellis2LoadModel_GGUF", "inputs": {"modelname": "TRELLIS.2-4B", "model_format": "GGUF Q8_0",
          "backend": "sdpa", "device": "cuda", "low_vram": True, "keep_models_loaded": False}}
P["2"] = {"class_type": "Trellis2LoadMesh_GGUF", "inputs": {"glb_path": "/mnt/sata/ComfyUI/_ashcase/closed_400k.glb"}}
views = {}
for i, v in enumerate(("front", "back", "left", "right")):
    a, b = str(10 + 2 * i), str(11 + 2 * i)
    P[a] = {"class_type": "Trellis2LoadImageWithTransparency_GGUF", "inputs": {"image": f"ash_case_{v}.png"}}
    P[b] = {"class_type": "Trellis2PreProcessImage_GGUF", "inputs": {"image": [a, 0], "padding": 25, "remove_background": False}}
    views[v] = [b, 0]
P["3"] = {"class_type": "Trellis2MeshTexturingMultiView_GGUF", "inputs": {
    "pipeline": ["1", 0], "trimesh": ["2", 0], "front_image": views["front"], "back_image": views["back"],
    "left_image": views["left"], "right_image": views["right"], "seed": 481516234, "texture_steps": 25,
    "texture_guidance_strength": 3.0, "texture_guidance_rescale": 0.2, "texture_rescale_t": 3.0,
    "resolution": "1024", "texture_size": 4096, "texture_alpha_mode": "OPAQUE", "double_side_material": False,
    "texture_guidance_interval_start": 0.0, "texture_guidance_interval_end": 0.9, "bake_on_vertices": False,
    "use_custom_normals": False, "uv_unwrap_method": "Xatlas", "mesh_cluster_threshold_cone_half_angle_rad": 60.0,
    "front_axis": "z", "blend_temperature": 1.0, "use_tiled_encoder": False, "encoder_tile_size": 512,
    "encoder_overlap": 24, "use_tiled_decoder_for_texture": False, "decoder_tile_size": 120,
    "decoder_overlap": 48, "sampler": "euler"}}
P["4"] = {"class_type": "Trellis2ExportMesh_GGUF", "inputs": {"trimesh": ["3", 0], "filename_prefix": "AshCase_Textured", "file_format": "glb"}}
r = urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8188/prompt", json.dumps({"prompt": P}).encode(), {"Content-Type": "application/json"}))
print(r.read().decode())
