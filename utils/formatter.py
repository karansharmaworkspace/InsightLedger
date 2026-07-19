import json


class DexpiFormatter:
    @staticmethod
    def sanitize_id(raw_type, counter):
        clean = "".join(c for c in raw_type if c.isalnum() or c == "_")
        if not clean:
            clean = "symbol"
        return f"{clean}{counter}"

    @staticmethod
    def to_user_schema(nodes, edges, metadata: dict | None = None):
        formatted_nodes = []
        id_map = {}
        counters = {}

        for i, node in enumerate(nodes):
            raw_type = node.get("type", node.get("label", "general"))
            coords = node.get("coordinates", [0, 0, 0, 0])

            label = raw_type

            counters[label] = counters.get(label, 0) + 1
            semantic_id = DexpiFormatter.sanitize_id(label, counters[label])
            id_map[node.get("id", f"node_{i}")] = semantic_id

            fine_class = node.get("type", "")
            fine_raw_id = node.get("fine_raw_id")

            formatted_node = {
                "id": semantic_id,
                "type_key": node.get("type_key", label),
                "attrs": {
                    "label": label,
                    "Labels": node.get("Labels", "N/A"),
                    "raw_id": node.get("raw_id", -1),
                    "fine_class": fine_class if fine_raw_id is not None else "",
                    "fine_raw_id": fine_raw_id if fine_raw_id is not None else "",
                    "xmin": round(float(coords[0]), 1),
                    "ymin": round(float(coords[1]), 1),
                    "xmax": round(float(coords[2]), 1),
                    "ymax": round(float(coords[3]), 1),
                    "loop_id": node.get("loop_id", ""),
                    "is_instrument": node.get("is_instrument", False),
                }
            }
            formatted_nodes.append(formatted_node)

        formatted_edges = []
        for edge in edges:
            if isinstance(edge, (tuple, list)):
                u, v = edge[:2]
                source_id = id_map.get(u, u)
                target_id = id_map.get(v, v)
                attrs = {"edge_label": edge[2] if len(edge) > 2 else "solid"}
            else:
                source_id = id_map.get(
                    edge.get("source", ""), edge.get("source", "")
                )
                target_id = id_map.get(
                    edge.get("target", ""), edge.get("target", "")
                )
                attrs = edge.get("attrs", {"edge_label": "solid"})

            attrs.setdefault("designPressure", "")
            attrs.setdefault("designTemperature", "")
            attrs.setdefault("pipeSpecification", "")
            attrs.setdefault("insulationClass", "")

            formatted_edges.append({"source": source_id, "target": target_id, "attrs": attrs})

        dexpi = {
            "@type": "DEXPI",
            "@schemaLocation": "https://www.dexpi.org/schema/1.3/DEXPI.xsd",
            "p&idHeader": {
                "project": (metadata or {}).get("project", ""),
                "plant": (metadata or {}).get("plant", ""),
                "documentNumber": (metadata or {}).get("documentNumber", ""),
                "revision": (metadata or {}).get("revision", ""),
                "description": (metadata or {}).get("description", ""),
            },
            "pipingNetwork": {
                "pipingNetworkItems": formatted_nodes,
                "pipingConnectors": formatted_edges,
            },
            # Top-level aliases for backward compat with GraphML export
            "nodes": formatted_nodes,
            "edges": formatted_edges,
        }

        return dexpi
