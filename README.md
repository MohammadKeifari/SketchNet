# SketchNet — Visual Machine Learning Editor

SketchNet is a drag‑and‑drop visual editor that lets you design neural networks on an infinite canvas and export them as clean, executable PyTorch code.  
No more boilerplate — just draw, connect, and export.

![SketchNet Canvas](static/images/logo_white.svg)

---

## Features

- **Visual Graph Editor** — place nodes (Layer, Conv2D, Dropout, etc.) on an infinite canvas, connect ports, and see tensor shapes propagate automatically.
- **Three‑Phase Code Generation** — every graph is split into preprocessing, training, and evaluation phases. The exported code is clean, with no runtime branching.
- **Dataset Management** — upload CSV, Excel, JSON, or Parquet files, or generate synthetic data. Shapes are inferred automatically.
- **Validation & Error Checking** — built‑in validator catches missing connections, phase mismatches, shape errors, and more before export.
- **Phase Highlighting** — colour‑code your graph by phase to see exactly which nodes are active during preprocessing, training, and evaluation.
- **Auto Layout** — automatically arrange nodes for a clean, readable graph.
- **Template System** — load pre‑built starter graphs (Linear Regression, CNN, Skip Connection) from the Learn page.
- **Validation Split & Early Stopping** — configure hold‑out validation directly in the Optimizer node.
- **Multi‑Input Concatenation** — layers accept multiple inputs and concatenate them along the feature dimension.
- **Visualisations** — scatter plots, histograms, 3‑D projections, with discrete or continuous colour mapping.
- **Undo / Redo** — full history support for all graph edits.
- **Copy / Paste** — copy and paste nodes and subgraphs across canvases.

---

## Tech Stack

| Layer              | Technology                                                          |
| ------------------ | ------------------------------------------------------------------- |
| Backend            | Django 5.x, Python 3.12                                             |
| Frontend           | Vanilla JavaScript (HTML5 Canvas)                                   |
| ML Code Generation | PyTorch, SymPy (symbolic shape propagation)                         |
| Data Processing    | Pandas, NumPy, Scikit‑learn (synthetic data)                        |
| Testing            | Django TestCase, custom PyTorch model runner                        |
| Styling            | CSS custom properties, theme support (light/dark/rose/forest/honey) |

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip / venv
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/SketchNet.git
cd SketchNet

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate    # Linux / macOS
.venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create a superuser (optional)
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```
