# RAMPR: Regional Analysis and Modeling for the Perennial Revolution

**RAMPR** is an open-source Python framework designed for the structural economic analysis of agricultural transitions. It provides tools to model the regional shifts associated with moving from annual monocultures to perennial-based agricultural systems.

---

## 💡 The Vision
The "Perennial Revolution" requires more than just biological breakthroughs; it requires an understanding of how regional economies adapt. RAMPR allows researchers to simulate:

* **Structural Shifts:** How labor and capital requirements change when transitioning to perennials.
* **Value Chain Impacts:** How regional input-output (I-O) tables shift as new perennial industries emerge.
* **Regional Modeling:** Granular analysis at the county, state, or watershed level.

## 📂 Repository Structure

```text
RAMPR/
├── data/                 # Metadata and processing scripts
│   ├── raw/              # Links/scripts to fetch raw USDA/BEA data
│   └── processed/        # Standardized regional economic profiles
├── docs/                 # Methodology and structural equation documentation
├── notebooks/            # EDA and case studies (e.g., Midwest Kernza Transition)
├── rampr/                # Core Python package
│   ├── data_io.py        # Data ingestion from API/local sources
│   ├── modeling.py      # Structural analysis and I-O logic
│   ├── spatial.py       # Regional mapping and GIS integration
│   └── utils.py         # Helper functions
├── tests/                # Unit tests for economic consistency
├── LICENSE               # Apache 2.0 or MIT
├── pyproject.toml        # Build system and dependencies
└── README.md             # Project overview
```

## 🚀 Quick Start
Installation
Ensure you have Python 3.9+ installed. It is recommended to use a virtual environment.

```
git clone [https://github.com/your-username/rampr.git](https://github.com/your-username/rampr.git)
cd rampr
pip install -e .
```

## Basic Usage
```
import rampr

# Initialize a model for a specific FIPS code (e.g., a region in Minnesota)
model = rampr.RegionalModel(region_id="27") 

# Apply a transition scenario: 15% conversion to perennial grains
scenario = model.apply_transition(perennial_share=0.15)

# View the structural impact on regional employment
print(scenario.employment_multiplier())
```

## 📊 Data Sources & Integration
RAMPR integrates multiple open-source data streams to build a comprehensive regional profile. We utilize a multi-layer approach to connect ecological change to economic outcomes.

USDA NASS: For crop yields, acreage, and production practices.

BEA (Bureau of Economic Analysis): For regional GDP and input-output data.

SSURGO/STATSGO2: For soil productivity and carbon sequestration potential.

Note: Raw data files are not stored in this repository due to size. Use rampr.download_sources() to fetch data to your local machine.


## 🤝 Contributing
We welcome contributions from economists, agronomists, and developers!

Fork the Project.

Create your Feature Branch (git checkout -b feature/NewModel).

Commit your changes (git commit -m 'Add some NewModel').

Push to the Branch (git push origin feature/NewModel).

Open a Pull Request.

## 📜 License
Distributed under the MIT License. See LICENSE for more information.
