import matplotlib.pyplot as plt
import matplotlib.patches as patches

def create_diagram(filename, nodes, edges, title):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')
    ax.set_title(title, fontsize=14, pad=20)

    # Draw Nodes
    for name, (x, y, color) in nodes.items():
        # Box
        rect = patches.FancyBboxPatch((x, y), 2, 1, boxstyle="round,pad=0.1", 
                                      linewidth=1, edgecolor='black', facecolor=color)
        ax.add_patch(rect)
        # Text
        ax.text(x + 1, y + 0.5, name, ha='center', va='center', fontsize=10, fontweight='bold')

    # Draw Edges
    for start, end, label in edges:
        x1, y1 = nodes[start][0] + 1, nodes[start][1] + 1  # Top Center? No, let's adjust based on relative pos
        x2, y2 = nodes[end][0] + 1, nodes[end][1]

        # Simple logic: connected centers
        sx, sy = nodes[start][0] + 1, nodes[start][1] + 0.5
        ex, ey = nodes[end][0] + 1, nodes[end][1] + 0.5
        
        # Adjust for box edges
        if sx < ex: # Right
            sx += 1
            ex -= 1
        elif sx > ex: # Left
            sx -= 1
            ex += 1
        elif sy < ey: # Up
            sy += 0.5
            ey -= 0.5
        elif sy > ey: # Down
            sy -= 0.5
            ey += 0.5

        ax.annotate("", xy=(ex, ey), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle="->", lw=1.5))
        
        # Label
        mid_x = (sx + ex) / 2
        mid_y = (sy + ey) / 2
        if label:
            ax.text(mid_x, mid_y, label, ha='center', va='center', fontsize=8, 
                    bbox=dict(facecolor='white', edgecolor='none', alpha=0.7))

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close()
    print(f"Created {filename}")

def main():
    # Colors
    c_hw = '#add8e6' # Blue
    c_sw = '#90ee90' # Green
    c_cl = '#ffcccb' # Red/Cloud

    # 1. Gate Unit Diagram
    nodes_gate = {
        "RFID Card": (0.5, 4, c_hw),
        "Raspberry Pi": (4, 4, c_sw),
        "Local JSON DB": (4, 1.5, c_sw),
        "GSM Module": (7.5, 4, c_hw),
        "Google Sheets": (4, 0, c_cl)
    }
    edges_gate = [
        ("RFID Card", "Raspberry Pi", "Scan"),
        ("Raspberry Pi", "Local JSON DB", "Validate"),
        ("Raspberry Pi", "GSM Module", "Send SMS"),
        ("Raspberry Pi", "Google Sheets", "Async Sync")
    ]
    create_diagram("diagram_gate.png", nodes_gate, edges_gate, "Figure 5.1: Gate Unit Data Flow")

    # 2. Bus Unit Diagram
    nodes_bus = {
        "RFID Card": (0.5, 4, c_hw),
        "ESP32": (4, 4, c_sw),
        "SIM800L (GPRS)": (4, 2, c_hw),
        "Google Script": (7.5, 2, c_cl),
        "Google Sheet": (7.5, 4, c_cl)
    }
    edges_bus = [
        ("RFID Card", "ESP32", "Scan"),
        ("ESP32", "SIM800L (GPRS)", "Data Request"),
        ("SIM800L (GPRS)", "Google Script", "HTTPS GET"),
        ("Google Script", "Google Sheet", "Query/Log"),
        ("Google Script", "SIM800L (GPRS)", "Response (Name/Phone)")
    ]
    create_diagram("diagram_bus.png", nodes_bus, edges_bus, "Figure 5.2: Bus Unit Data Flow")

    # 3. Deployment Architecture
    nodes_arch = {
        "Gate Unit\n(Edge)": (1, 3, c_sw),
        "Bus Unit\n(Mobile)": (7, 3, c_hw),
        "Cloud Backend\n(Google)": (4, 5, c_cl),
        "Parents\n(SMS)": (4, 1, c_hw)
    }
    edges_arch = [
        ("Gate Unit\n(Edge)", "Cloud Backend\n(Google)", "Sync"),
        ("Bus Unit\n(Mobile)", "Cloud Backend\n(Google)", "Validation"),
        ("Gate Unit\n(Edge)", "Parents\n(SMS)", "Notify"),
        ("Bus Unit\n(Mobile)", "Parents\n(SMS)", "Notify")
    ]
    create_diagram("diagram_arch.png", nodes_arch, edges_arch, "Figure 5.4: Deployment Architecture")

if __name__ == "__main__":
    main()
