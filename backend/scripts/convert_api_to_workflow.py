#!/usr/bin/env python3
"""
Convert ComfyUI API-format workflow JSON (the flat {"1": {...}, "2": {...}}
structure used to POST to /prompt) into full workflow-format JSON that can
be drag-and-dropped into the ComfyUI web UI and rendered as a visual graph.

Requires a running ComfyUI instance so it can fetch /object_info and know
each node's real input/output schema (which inputs are sockets vs widgets,
output types, etc). This makes the conversion accurate instead of guessed.

Usage:
    python3 convert_api_to_workflow.py file1.json [file2.json ...] \
        [--server http://127.0.0.1:8081] [--outdir ./workflow_format]

Output:
    <outdir>/<original_name>_workflow.json  (one per input file)
"""
import json
import sys
import os
import argparse
import urllib.request

PRIMITIVE_WIDGET_TYPES = {"INT", "FLOAT", "STRING", "BOOLEAN"}

# Stable schemas for ComfyUI's built-in core nodes, used as a fallback (or
# primary source) so conversion still works correctly even if the live
# ComfyUI server can't be reached. Custom nodes (e.g. PhotoMakerLoader,
# PhotoMakerEncode) still rely on the live /object_info fetch.
BUILTIN_SCHEMAS = {
    "CheckpointLoaderSimple": {
        "input": {"required": {"ckpt_name": [["*"], {}]}},
        "output": ["MODEL", "CLIP", "VAE"],
        "output_name": ["MODEL", "CLIP", "VAE"],
    },
    "CLIPTextEncode": {
        "input": {"required": {"text": ["STRING", {"multiline": True}], "clip": ["CLIP", {}]}},
        "output": ["CONDITIONING"],
        "output_name": ["CONDITIONING"],
    },
    "EmptyLatentImage": {
        "input": {"required": {"width": ["INT", {}], "height": ["INT", {}], "batch_size": ["INT", {}]}},
        "output": ["LATENT"],
        "output_name": ["LATENT"],
    },
    "KSampler": {
        "input": {"required": {
            "model": ["MODEL", {}],
            "seed": ["INT", {"control_after_generate": True}],
            "steps": ["INT", {}],
            "cfg": ["FLOAT", {}],
            "sampler_name": [["*"], {}],
            "scheduler": [["*"], {}],
            "positive": ["CONDITIONING", {}],
            "negative": ["CONDITIONING", {}],
            "latent_image": ["LATENT", {}],
            "denoise": ["FLOAT", {}],
        }},
        "output": ["LATENT"],
        "output_name": ["LATENT"],
    },
    "VAEDecode": {
        "input": {"required": {"samples": ["LATENT", {}], "vae": ["VAE", {}]}},
        "output": ["IMAGE"],
        "output_name": ["IMAGE"],
    },
    "SaveImage": {
        "input": {"required": {"images": ["IMAGE", {}], "filename_prefix": ["STRING", {}]}},
        "output": [],
        "output_name": [],
    },
    "LoadImage": {
        "input": {"required": {"image": [["*"], {"image_upload": True}]}},
        "output": ["IMAGE", "MASK"],
        "output_name": ["IMAGE", "MASK"],
    },
}

SEED_INPUT_NAMES = {"seed", "noise_seed"}


def fetch_object_info(server, class_types):
    info = {}
    for ct in sorted(class_types):
        if ct in BUILTIN_SCHEMAS:
            info[ct] = BUILTIN_SCHEMAS[ct]
            print(f"  ✓ {ct}: using built-in schema (no server needed)")
            continue
        url = f"{server}/object_info/{ct}"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.load(resp)
                if ct in data:
                    info[ct] = data[ct]
                    print(f"  ✓ {ct}: fetched live schema from {server}")
                else:
                    print(f"  ⚠ {ct}: server responded but has no info for this node "
                          f"(best-effort guessing will be used)", file=sys.stderr)
        except Exception as e:
            print(f"  ⚠ {ct}: could not reach {server} ({e}) — "
                  f"is ComfyUI actually running and at that address? "
                  f"(best-effort guessing will be used)", file=sys.stderr)
    return info


def input_order(node_info):
    order = []
    inp = node_info.get("input", {})
    for name, spec in inp.get("required", {}).items():
        order.append((name, spec))
    for name, spec in inp.get("optional", {}).items():
        order.append((name, spec))
    return order


def convert(api_json, object_info):
    nodes_data = {k: v for k, v in api_json.items() if k != "_meta"}
    node_ids = sorted(nodes_data.keys(), key=lambda x: int(x))

    node_entries = {}
    x, y, x_step = 40, 200, 320
    for i, nid in enumerate(node_ids):
        n = nodes_data[nid]
        class_type = n["class_type"]
        title = n.get("_meta", {}).get("title", class_type)
        node_entries[nid] = {
            "id": int(nid),
            "type": class_type,
            "pos": [x + i * x_step, y],
            "size": [270, 140],
            "flags": {},
            "order": i,
            "mode": 0,
            "inputs": [],
            "outputs": [],
            "properties": {"Node name for S&R": class_type},
            "widgets_values": [],
            "title": title,
        }

    # Fill widgets / socket-input placeholders / outputs
    for nid in node_ids:
        n = nodes_data[nid]
        class_type = n["class_type"]
        entry = node_entries[nid]
        info = object_info.get(class_type)
        api_inputs = n.get("inputs", {})

        if info is None:
            for name, val in api_inputs.items():
                if isinstance(val, list) and len(val) == 2 and str(val[0]) in nodes_data:
                    entry["inputs"].append({"name": name, "type": "*", "link": None})
                else:
                    entry["widgets_values"].append(val)
                    # Even with zero schema info, a field literally named
                    # "seed"/"noise_seed" holding an int is, in practice,
                    # always paired with an auto-injected control_after_generate
                    # widget in the real ComfyUI UI. Insert the placeholder so
                    # later widget values don't shift out of alignment.
                    if name in SEED_INPUT_NAMES and isinstance(val, int):
                        entry["widgets_values"].append("fixed")
            continue

        for name, spec in input_order(info):
            if name not in api_inputs:
                continue
            val = api_inputs[name]
            if isinstance(val, list) and len(val) == 2 and str(val[0]) in nodes_data:
                socket_type = "COMBO" if isinstance(spec[0], list) else spec[0]
                entry["inputs"].append({"name": name, "type": socket_type, "link": None})
            else:
                entry["widgets_values"].append(val)
                # ComfyUI's frontend auto-injects a "control after generate"
                # widget right after any seed-like INT input flagged with
                # control_after_generate. The API-format JSON has no value
                # for it, so we insert a placeholder to keep everything
                # after this point aligned with the real widget order.
                has_flag = (len(spec) > 1 and isinstance(spec[1], dict)
                            and spec[1].get("control_after_generate"))
                if has_flag or (name in SEED_INPUT_NAMES and isinstance(val, int)):
                    entry["widgets_values"].append("fixed")

        out_types = info.get("output") or []
        out_names = info.get("output_name") or out_types
        for oi, otype in enumerate(out_types):
            oname = out_names[oi] if oi < len(out_names) else otype
            entry["outputs"].append({"name": oname, "type": otype, "links": [], "slot_index": oi})

    # Build links
    links = []
    link_id = 1
    for nid in node_ids:
        n = nodes_data[nid]
        entry = node_entries[nid]
        for name, val in n.get("inputs", {}).items():
            if not (isinstance(val, list) and len(val) == 2 and str(val[0]) in nodes_data):
                continue
            origin_nid, origin_slot = str(val[0]), int(val[1])
            origin_entry = node_entries[origin_nid]
            target_input = next((ip for ip in entry["inputs"] if ip["name"] == name), None)
            if target_input is None:
                target_input = {"name": name, "type": "*", "link": None}
                entry["inputs"].append(target_input)

            if origin_slot >= len(origin_entry["outputs"]):
                # Origin node's schema wasn't available, so we don't know
                # how many outputs it has. Grow the list on demand rather
                # than dropping the link.
                while len(origin_entry["outputs"]) <= origin_slot:
                    origin_entry["outputs"].append({
                        "name": "*", "type": "*", "links": [],
                        "slot_index": len(origin_entry["outputs"]),
                    })
            link_type = origin_entry["outputs"][origin_slot]["type"]

            idx = next(i for i, ip in enumerate(entry["inputs"]) if ip is target_input)
            links.append([link_id, int(origin_nid), origin_slot, int(nid), idx, link_type])
            target_input["link"] = link_id
            if origin_slot < len(origin_entry["outputs"]):
                origin_entry["outputs"][origin_slot]["links"].append(link_id)
            link_id += 1

    nodes = [node_entries[nid] for nid in node_ids]
    return {
        "last_node_id": max(int(n) for n in node_ids),
        "last_link_id": link_id - 1,
        "nodes": nodes,
        "links": links,
        "groups": [],
        "config": {},
        "extra": {"ds": {"scale": 1, "offset": [0, 0]}},
        "version": 0.4,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="API-format workflow JSON files to convert")
    ap.add_argument("--server", default="http://127.0.0.1:8081",
                     help="Running ComfyUI base URL (default: http://127.0.0.1:8081)")
    ap.add_argument("--outdir", default="./workflow_format",
                     help="Output directory (default: ./workflow_format)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    all_class_types = set()
    parsed = {}
    for f in args.files:
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        parsed[f] = data
        for k, v in data.items():
            if k != "_meta" and isinstance(v, dict) and "class_type" in v:
                all_class_types.add(v["class_type"])

    print(f"Fetching node schemas from {args.server} ...")
    object_info = fetch_object_info(args.server, all_class_types)

    for f, data in parsed.items():
        workflow = convert(data, object_info)
        base = os.path.splitext(os.path.basename(f))[0]
        out_path = os.path.join(args.outdir, f"{base}_workflow.json")
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(workflow, fh, indent=2)
        print(f"  → wrote {out_path}")

    print("\nDone. Drag the files from the output directory into the ComfyUI canvas.")


if __name__ == "__main__":
    main()