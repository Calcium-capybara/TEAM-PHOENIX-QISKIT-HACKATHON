import json
import networkx as nx
import matplotlib.pyplot as plt

with open('instances.json') as f:
    edges = json.load(f)['PS-O1']['weighted_edges']

G = nx.Graph()
for u, v, w in edges:
    G.add_edge(u, v, weight=w)

# Optimal partition: {0, 1, 3} vs {2, 4, 5}
colors = ['#ff4d4d' if node in {0, 1, 3} else '#4da6ff' for node in G.nodes()]

plt.figure(figsize=(8, 6))
pos = nx.spring_layout(G, seed=42)
nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=900, edgecolors='black', linewidths=2)
nx.draw_networkx_labels(G, pos, font_size=14, font_weight='bold', font_color='white')

# Draw edges
cut_edges = [(u, v) for u, v, d in G.edges(data=True) if (u in {0, 1, 3}) != (v in {0, 1, 3})]
uncut_edges = [(u, v) for u, v, d in G.edges(data=True) if (u in {0, 1, 3}) == (v in {0, 1, 3})]

nx.draw_networkx_edges(G, pos, edgelist=cut_edges, edge_color='#e60000', width=3, style='dashed', label='Cut Edges (Weight = 22)')
nx.draw_networkx_edges(G, pos, edgelist=uncut_edges, edge_color='#a6a6a6', width=2, style='solid', label='Uncut Edges')

edge_labels = {(u, v): f"w={d['weight']}" for u, v, d in G.edges(data=True)}
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=11, font_color='#222')

plt.title('PS-O1 Locked Problem Graph & Optimal Max-Cut Partition (C* = 22.0)', fontsize=13, fontweight='bold')
plt.legend(loc='upper right')
plt.axis('off')
plt.tight_layout()
print('Displaying interactive graph window... Close the window when done.')
plt.show()
