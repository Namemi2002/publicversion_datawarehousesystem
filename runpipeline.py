from src import orchestrator
import pymysql
mysql_connection = pymysql.connect(
    host = orchestrator.configinfo['datawarehouseconfig']['connection']['host'],
    user = orchestrator.configinfo['datawarehouseconfig']['connection']['user'],
    password = orchestrator.configinfo['datawarehouseconfig']['connection']['password'],
    database = orchestrator.configinfo['datawarehouseconfig']['connection']['database'],
    port = orchestrator.configinfo['datawarehouseconfig']['connection']['port']
)

# The following is all possible pipelines. Choose which pipelines can run by commenting remaining others
orchestrator.run_ghtk_exceletl(mysql_connection)
orchestrator.run_ghn_exceletl(mysql_connection)
orchestrator.run_jte_exceletl(mysql_connection)
orchestrator.run_spx_exceletl(mysql_connection)
orchestrator.run_codtvc_apietl(mysql_connection)
orchestrator.run_cusbank_apietl(mysql_connection)
orchestrator.run_internalprice_apietl(mysql_connection)
orchestrator.run_returnedorderscan_apietl(mysql_connection)
orchestrator.run_deliveryorderscan_apietl(mysql_connection)
orchestrator.run_deliveryordershandlingteam_apietl(mysql_connection)
orchestrator.run_jtetransactions_exceletl(mysql_connection)
orchestrator.run_spxtransactions_exceletl(mysql_connection)
orchestrator.run_ghntransactions_exceletl(mysql_connection)
orchestrator.run_ghncointransactions_exceletl(mysql_connection)
orchestrator.run_tiktokincome_exceletl(mysql_connection)
orchestrator.run_nhanhvn_apietl(mysql_connection)
orchestrator.run_shopee_apietl(mysql_connection)
orchestrator.run_tiktok_apietl(mysql_connection)
orchestrator.run_sqlscript(orchestrator.LAKETOWAREHOUSE_QUERYPATH, mysql_connection)
orchestrator.updatereport_googlesheet(mysql_connection)

mysql_connection.close()
print('Program finished!')