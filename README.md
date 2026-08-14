# Qualifyze Challenge
This repository contains the development behind the interview of Jordi Ripoll Melis. More details about the challenge in this [document](docs/2025_Case_Study__AI_Data_Scientist.docx.pdf).

# Context
This section is intended as a descriptive section of the business problem and gather all the knowledge behind the use case.

The main objective is to assess the risk of future non-compliance (or inspections) for a given supplier based on historical data (such as audit data and warning letters). 

Inspections are identified by the **FEI** code (**FDA Establishment Identifier**) which is usually an individual supplier facility/site. Notice one company can operate on several facilities with different compliance histories ([Inspections Database FAQ](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/inspection-references/inspections-database-frequently-asked-questions)).

**FDA** is the [**Food and Drug Administration**](https://en.wikipedia.org/wiki/Food_and_Drug_Administration), a federal agency of the United States Department of Health and Human Services. It conducts inspections and assessments of regulated facilities to determine a firm's compliance with applicable laws and regulations, such as the Food, Drug, and Cosmetic Act. This typically involves an investigator visiting a firm’s location ([Inspections Database FAQ](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/inspection-references/inspections-database-frequently-asked-questions)).

After an inspection, FDA determines the compliance of a FEI with the following [classification](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/inspection-basics/inspection-classifications):
* No Action Indicated (**NAI**) classification indicates a facility is in an acceptable state of compliance. The facility, usually, was not issued a Form FDA 483 or FDA-4056 at the conclusion of the inspection.
* Voluntary Action Indicated (**VAI**) classification indicates the inspection found objectionable conditions or practices but the agency has determined the facility can voluntarily correct its deficiencies and will not recommend any action. Usually, the facility was issued a Form FDA 483 or FDA-4056 at the conclusion of the inspection.
* Official Action Indicated (**OAI**) classification indicates a facility is in an unacceptable state of compliance. The facility may have been issued a Form FDA-483 or FDA-4056 at the conclusion of the inspection.

An [**FDA form 483**](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/inspection-references/fda-form-483-frequently-asked-questions) is issued to firm management at the conclusion of an inspection when an investigator(s) has observed any conditions that in their judgment may constitute violations of the Food Drug and Cosmetic (FD&C) Act and related Acts.

To sum up, there are to relevant events that we will focus in this use-case, the inspection and in case of being inspected, which classification does the FEI receive:
* [Risk-based approach to Inspections](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/inspection-basics/fdas-risk-based-approach-inspections): FDA explicitly gives the example that an uninspected sterile-drug manufacturer producing narrow-therapeutic-index drugs would likely be considered higher risk than a previously inspected facility producing conventional over-the-counter tablets.

Other important notes:
* FDA states that its public inspections database is [not comprehensive](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/inspection-references/inspections-database-frequently-asked-questions) "since not all inspections are disclosed".
* [Glossary](https://datadashboard.fda.gov/oii/glossary.htm#headingSeven) of topic-related terms from the FDA.

# Repository

## Installation

For this use-case we are working with Python 3.13. Install it before running other commands and verify its version with `python --version`, checking it returns `Python 3.13.x`.

Install environment with the following sequence of commands:
```{bash}
uv sync
uv run pytest
uv run qualifyze-case-study
```

## Dependencies
Several other documents must be inserted to make the project properly work.

### Datasets
Some datasets must be added into the `/data` folder. Ideally this should be automated leveraging the [Data Dashboard API Usage](https://datadashboard.fda.gov/oii/api/index.htm). But we will limit the development of this use case to excel files directly downloaded into the `/data` folder to simplify things, as there is needed an authorization to use the API. The following tables have been considered (and their corresponding file name they must take in order to work):
* [Inspections](https://datadashboard.fda.gov/oii/cd/inspections.htm) (inspections.xlsx)
* [Inspection citations](https://datadashboard.fda.gov/oii/cd/inspections.htm) (inspection-citations.xlsx)
* [Compliance actions](https://datadashboard.fda.gov/oii/cd/complianceactions.htm) (compliance-actions.xlsx)
* [Recall details](https://datadashboard.fda.gov/oii/cd/recalls.htm) (recall-details.xlsx)

## Management

The repository libraries are managed with [uv](https://docs.astral.sh/uv/).

Tests are handled using [pytest](https://docs.pytest.org/en/stable/).

Linting is ran with [ruff](https://docs.astral.sh/ruff/).

## Components

### Collectors

There are several services to keep data updated:

* FDA ingestion: Ingestion of data from FDA public xlsx files. In particular, data from inspections, inspection citations, compliance actions and recalls.
* Warning Letters: There is a service to collect available [warning letters](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters) automatically. There is a crawler that iterates over all the warning letters retrieving the information from each warning letter URL each 30 seconds (as mentioned in its [robots.txt](https://www.fda.gov/robots.txt) file).

### Database

A Database has been build within a Docker container, in particular a PostgreSQL database. Here we can find different repoistories:
- Warning Letters: Repository containing information about Warning Letters.

The container can be run and check it's running with the following commands:
```{bash}
docker compose up -d db
docker compose ps
```