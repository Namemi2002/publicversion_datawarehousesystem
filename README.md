# END-TO-END DATA WAREHOUSE SYSTEM

## 1. Overview
This project builds a complete ***end-to-end Data Warehouse system*** for a medium-sized online fashion company. It automates the collection, transformation, integration, and historical storage of order, customer, product, and financial data for reporting and analysis.

This system has been deployed in a ***real business environment*** with its business impact summarized in the next section.

## 2. Business Problems
### Before
Before this project, operational data was managed and analyzed manually using *Google Sheets* and *Microsoft Excel*. As the business grew, this workflow became increasingly inefficient and difficult to maintain, results in 3 major problems:
- **Time & effort - consuming report generation**
  - 5 employees were responsible for creating frequent reports. Although reporting was not their primary responsibility, each person had to spend about 2 hours per day generating reports manually, resulting in around 10 working hours being wasted every day.
- **Inconsistent accuracy**
  - Since data had to be downloaded, cleaned, and transformed manually, random human errors frequently occurred. Therefore, different reports sometimes contained inconsistent figures, reducing confidence in the reported results.
- **Limited data utilization**
  - Analysts spent considerable time locating the required data sources, verifying that historical data was still available, and manually cleaning datasets with inconsistent formats. This made performing diagnostic analysis very difficult, while predictive analysis was even nearly impossible.
### After
Those problems require a data processing & storage solution, a Data Warehouse system is perfectly fit with following impacts after in production:
- **Report generation**
  - By automating data extraction, cleaning, transformation, and loading through the ETL pipelines along with API integration, the total time creating reports has been reduced to 30 minutes per day, down 95%.
- **Accuracy**
  - Data is cleaned and standardized using a consistent set of transformation rules throughout pipelines with multiple validation checkpoints; ensuring all reports are generated from accurate and consistent data.
- **Data Utilization**
  - The Data Warehouse stores cleaned and standardized historical data, providing a Single Source of Truth for the organization, data now is already available for higher level analysis.

## 3. Technical Highlights
In addition to business impacts, the Data Warehouse system was designed with the following technical advantages:
- **Free to deploy**
  - The system is built entirely with Python 3.13 and MySQL Community Server 8.0, allowing it to be deployed on a local machine without any software licensing costs.
- **Easy to use**
  - The system is designed so that even non-tech users can operate ETL pipelines. Daily operation requires configuring only two files: runpipeline.py to select which pipeline to execute, and pipelineconfig.yaml to configure how each pipeline should run.
- **Ready to scale up**
  - The system adopts a modular architecture where each class and function is responsible for a single task. This minimizes dependencies between components, making the system easier to maintain, extend, and scale as new data sources or ETL pipelines are added.

## 4. Data Warehouse System Architecture
The design of this Data Warehouse system follows classic warehouse design with 4 components: Source Layer, ETL pipelines, Storage Layer, and Reporting Layer
<img width="1201" height="712" alt="DW system architecture_Github post" src="https://github.com/user-attachments/assets/14d6db89-b074-45fb-b609-8fe69398bd1f" />
**The Source Layer** is where data is generated. This system currently supports two types of data sources:
 - API-based sources.
 - Excel-based sources.

**The ETL Pipelines** are designed for batch processing and follow a modular architecture in which each module contains classes and functions responsible for a single task. The architecture consists of four modules:
 - Extractor: responsible for extracting data from source systems.
 - Cleaner: responsible for cleaning, transforming, and standardizing data.
 - Loader: responsible for loading data to target.
 - Orchestrator: coordinates end-to-end ETL workflows by combining the above modules.

**The Storage Layer** is the heart of entire Data Warehouse system with two-logical layer architecture design consisting of a Data Lake and a Data Warehouse:
 - Data Lake stores data extracted from source with minimal transformation, serving as a staging area and recovery source for the warehouse.
 - Data Warehouse organizes cleaned and standardized data into a Star Schema with 1 fact and 5 dimensions.
 - Change Data Capture (CDC) is implemented using different incremental loading strategies based on the capabilities of each data source.

**The Report Layer** provides stakeholders with access to business reports and dashboards through two reporting interfaces:
 - Google Sheets for operational reports.
 - Power BI for interactive dashboards and data visualization.

## 5. How to Use
### Prerequisites
Before running the system, complete the following setup steps:
- Install Python 3.13 and MySQL Server 8.0.46
- Set up a Python environment and install required libraries using requirements.txt
- Execute all SQL scripts in:
  - rootdir/warehouse/datalake/createtables.sql
  - rootdir/warehouse/datawarehouse/createtables.sql
- Configure the required API credentials:
  - Place the Google Service Account JSON credential file (used by gspread) in rootdir/secretkey/
  - Create a Google Sheets file containing two worksheets to store the Shopee and TikTok API credentials (see [example](https://docs.google.com/spreadsheets/d/1ttsjkMV-tVjvQkbd-FynnCiYT-SUyVN6ipz9-A-zSqQ/edit?gid=0#gid=0)). Only manually fill in all fields before the first time running this Data Warehouse system.
  - Complete the remaining configuration in rootdir/secretkey/key.yaml following the instructions provided in the file.
- (Optional) If you want to generate Google Sheets reports, create a Google Sheets file with the required worksheet fields (see [example](https://docs.google.com/spreadsheets/d/1Tdo8pOpzuwyc7Bb1VbLxE6lqQLsjQyVn0u_iZJHcaiU/edit?gid=0#gid=0)). Manually fill in all fields.
### Running the Data Warehouse System
To execute the ETL pipelines and update the reports:
- Download the required Excel source files (if needed).
- Configure runpipeline.py to specify which pipeline(s) to execute.
- Configure pipelineconfig.yaml to define how each selected pipeline should run.
