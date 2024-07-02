let network;
let selectedNode;
let isCtrlPressed = false;
let firstSelectedNode = null;

function analyzeText() {
    const text = document.getElementById('input-text').value;
    
    // Verifica que el texto no esté vacío
    if (!text.trim()) {
        alert('Por favor, ingresa algún texto para analizar.');
        return;
    }
            
    fetch('/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: text }),
    })
    .then(response => response.json())
    .then(data => {
        const container = document.getElementById('mynetwork');
        const options = {
            nodes: {
                shape: 'dot',
                scaling: {
                    min: 10,
                    max: 30,
                    label: {
                        enabled: true,
                        min: 14,
                        max: 30,
                        maxVisible: 30,
                        drawThreshold: 5
                    }
                },
                color: {
                    background: 'rgba(255, 255, 255, 0.1)',
                    border: 'rgba(255, 255, 255, 0.3)',
                    highlight: {
                        background: 'rgba(255, 255, 255, 0.2)',
                        border: 'rgba(255, 255, 255, 0.5)'
                    }
                },
                font: {
                    color: '#FFFFFF',
                    size: 14
                }
            },
            edges: {
                color: {
                    color: '#FFFFFF',
                    highlight: '#00BFFF'
                },
                scaling: {
                    min: 1,
                    max: 10
                },
                smooth: {
                    type: 'continuous'
                }
            },
            physics: {
                forceAtlas2Based: {
                    gravitationalConstant: -50,
                    centralGravity: 0.01,
                    springLength: 100,
                    springConstant: 0.08
                },
                maxVelocity: 50,
                solver: 'forceAtlas2Based',
                timestep: 0.35,
                stabilization: { iterations: 150 },
                barnesHut: {
                    gravitationalConstant: -2000,
                    centralGravity: 0.3,
                    springLength: 95,
                    springConstant: 0.04,
                    damping: 0.09,
                    avoidOverlap: 0
                },
                repulsion: {
                    centralGravity: 0.2,
                    springLength: 200,
                    springConstant: 0.05,
                    nodeDistance: 100,
                    damping: 0.09
                }
            },
            interaction: {
                hover: true,
                hoverConnectedEdges: true,
                selectConnectedEdges: true
            }
        };

        data.nodes.forEach(node => {
            if (node.sentiment === 'positive') {
                node.color = {
                    background: '#FDB400',
                    border: '#FFFFFF'
                };
            } else if (node.sentiment === 'negative') {
                node.color = {
                    background: '#1F2833',
                    border: '#FFFFFF'
                };
            }
        });

        if (network) {
            network.setData(data);
        } else {
            network = new vis.Network(container, data, options);
            network.on("selectNode", function(params) {
                if (params.nodes.length == 1) {
                    var nodeId = params.nodes[0];
                    if (isCtrlPressed) {
                        if (firstSelectedNode === null) {
                            firstSelectedNode = nodeId;
                        } else {
                            createEdge(firstSelectedNode, nodeId);
                            firstSelectedNode = null;
                        }
                    } else {
                        selectedNode = nodeId;
                        showSentimentPanel();
                        document.onkeydown = function(e) {
                            if (e.key === "Delete") {
                                if (confirm("¿Estás seguro de que quieres eliminar este nodo?")) {
                                    removeNode(nodeId);
                                    hideSentimentPanel();
                            }
                        }
                    };
                }}
            });
            network.on("deselectNode", function(params) {
                hideSentimentPanel();
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Hubo un error al analizar el texto. Por favor, intenta de nuevo.');
    });
    document.getElementById('input-text').value = '';
}

function showSentimentPanel() {
    document.getElementById('sentiment-panel').style.display = 'block';
}

function hideSentimentPanel() {
    document.getElementById('sentiment-panel').style.display = 'none';
}

function assignSentiment(sentiment) {
    if (selectedNode) {
        fetch('/update_sentiment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ node_id: selectedNode, sentiment: sentiment }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                updateNodeColor(selectedNode, sentiment);
                hideSentimentPanel();
            } else {
                console.error('Error al actualizar el sentimiento:', data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
}

function updateNodeColor(nodeId, sentiment) {
    let color = {};
    if (sentiment === 'positive') {
        color = {
            background: '#FDB400',
            border: '#FFFFFF'
        };
    } else if (sentiment === 'negative') {
        color = {
            background: '#1F2833',
            border: '#FFFFFF'
        };
    } else {
        // Para sentimiento neutro, volvemos al color original
        color = null;
    }
    network.body.data.nodes.update({ id: nodeId, color: color });

    // Actualizar la física del nodo
    let mass = (sentiment === 'positive' || sentiment === 'negative') ? 2 : 1;
    network.body.data.nodes.update({ id: nodeId, mass: mass });

    // Recalcular la física
    network.physics.solver.init(network.body);
    network.redraw();
}

function removeNode(nodeId) {
    fetch('/remove_node', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ node_id: nodeId }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            network.deleteSelected();
            network.fit(); // Re-ajustar la vista
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Hubo un error al eliminar el nodo. Por favor, intenta de nuevo.');
    });
}

function createEdge(fromNode, toNode) {
    if (fromNode === toNode) {
        alert("No se puede conectar un nodo consigo mismo.");
        return;
    }

    let edgeId = `${fromNode}-${toNode}`;
    let reverseEdgeId = `${toNode}-${fromNode}`;

    // Verifica si ya existe una conexión entre estos nodos
    if (network.body.data.edges.get(edgeId) || network.body.data.edges.get(reverseEdgeId)) {
        alert("Ya existe una conexión entre estos nodos.");
        return;
    }

    fetch('/create_edge', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ from: fromNode, to: toNode }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            network.body.data.edges.add({
                id: edgeId,
                from: fromNode,
                to: toNode
            });
            network.redraw();
        } else {
            console.error('Error al crear la conexión:', data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Hubo un error al crear la conexión. Por favor, intenta de nuevo.');
    });
}

function clearAll() {
    fetch('/clear', {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "cleared") {
            if (network) {
                network.setData({ nodes: [], edges: [] });
            }
            document.getElementById('input-text').value = '';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Hubo un error al limpiar. Por favor, intenta de nuevo.');
    });
}

function toggleSpecialNode() {
    if (selectedNode) {
        fetch('/toggle_special_node', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ node_id: selectedNode }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                updateNodeAppearance(selectedNode, data.is_special);
                console.log("Nodo alternado a especial:", data.is_special);
            } else {
                console.error('Error al alternar nodo especial:', data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
}


function updateNodeAppearance(nodeId, isSpecial) {
    let color = isSpecial ? { background: 'rgba(138, 43, 226, 0.5)', border: '#FFFFFF' } : null; 
    let mass = isSpecial ? 2 : 1;

    network.body.data.nodes.update({
        id: nodeId,
        color: color,
        mass: mass,
        font: {
            color: isSpecial ? '#FFFFFF' : null
        }
    });

    // Forzar una actualización completa del nodo
    network.body.data.nodes.update({ id: nodeId });

    // Recalcular la física y redibujar
    network.physics.solver.init(network.body);
    network.stabilize();
    network.redraw();
}

document.addEventListener('keydown', function(event) {
    if (event.key === 'Control') {
        isCtrlPressed = true;
    }
});

document.addEventListener('keyup', function(event) {
    if (event.key === 'Control') {
        isCtrlPressed = false;
        firstSelectedNode = null;
    }
});

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('input-text').addEventListener('keypress', function(event) {

        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            analyzeText();
            document.getElementById('input-text').value = '';
        }
    });
});