-- DATALAKE TABLES:

create table nhanhvnorders (
	orderid varchar(40) not null primary key,
	created_at datetime,
	customername varchar(200),
	customerphonenumber varchar(40),
	customer_cityaddress varchar(60),
	customer_districtaddress varchar(60),
	deliverybrand varchar(40),
	trackingnumber varchar(40),
	orderstatus varchar(40),
	orderparentsource varchar(40),
	ordersource varchar(100),
	platform varchar(40),
	senddelivery_at datetime,
	cod_prepaid int,
	created_byperson varchar(60),
	internalnote varchar(255),
	customernote varchar(255),
	previousid_internalnote varchar(40),
	previousid_customernote varchar(40),
	is_wrongproduct boolean,
	dw_updatedat datetime not null
);

create table nhanhvnorderdetails (
	productid varchar(40) not null, -- for products haven't been created in the Product tab, they will show '' (empty string) value
	orderid varchar(40) not null,
	productbarcode varchar(40),
	parentproductid varchar(40),
	price int,
	discount_allproduct int,
	quantity int,
	dw_updatedat datetime not null,
	primary key (orderid, productid)
);

create table deliveryorders (
    delivery_orderid varchar(40) not null primary key,
    shop_orderid varchar(40),
    orderstatus varchar(40),
    cod_collected int,
    cod_declared int,
    shippingcost int,
    createdat datetime,
    pickupat datetime,
    completedat datetime,
    courier varchar(40),
    compensationvalue int,
    courieraccount varchar(40),
    dw_updatedat datetime not null
);

create table customerbanks (
    bank_surrogateid varchar(40) not null primary key,
    notedate date,
    orderid varchar(160),
    customerphonenumber varchar(40),
    bankvalue int,
    verifybyperson varchar(40),
    ftcode varchar(40),
    note varchar(255),
    dw_updatedat datetime not null,
    index idx_orderid (orderid)
);

create table returnedorders_scan (
    scan_surrogateid varchar(40) not null primary key,
    scanat date,
    delivery_orderid varchar(40),
    productid varchar(40),
    dw_updatedat datetime not null,
    index idx_delivery_orderid (delivery_orderid)
);

create table delivery_reconciliation (
    sessionid varchar(60) not null,
    delivery_orderid varchar(100) not null,
    reconciliation_value int,
    reconciliation_at datetime,
    courier varchar(40),
    reconciliation_content varchar(255),
    dw_updatedat datetime not null,
    primary key (delivery_orderid, sessionid)
);

create table handle_deliveryorders (
    delivery_orderid varchar(40) not null primary key,
    scan_deliveryorder_at date,
    handleteam_note1 varchar(255),
    handleteam_note2 varchar(255),
    handleteam_note3 varchar(255),
    dw_updatedat datetime not null
);

create table shopeeorders (
    orderid varchar(40) not null primary key,
    packageid varchar(40),
    courier varchar(40),
    createdat datetime,
    pickupat datetime,
    completedat datetime,
    orderstatus varchar(40),
    cancel_reason varchar(255),
    buyer_accountname varchar(255),
    returned_orderids varchar(255),
    buyer_paymentmethod varchar(100),
    collectedvalue_theory int,
    buyerpaidvalue int,
    shippingcost int,
    shippingcostdiscounted_byplatform int,
    shippingcostdiscounted_byseller int,
    delivery_orderid varchar(40),
    shopname varchar(160),
    dw_updatedat datetime not null
);

create table shopeeorderdetails (
    orderid varchar(40) not null,
    product_skuid varchar(40) not null,
    orderproduct_id varchar(100) not null,
    productid varchar(40),
    productname varchar(255),
    product_skuname varchar(255),
    quantity int,
    displayprice int,
    realprice int,
    shopdiscount_allquantities int,
    shopeediscount_allquantities int,
    dw_updatedat datetime not null,
    primary key (orderid, product_skuid, orderproduct_id)
);

create table tiktokorders (
    orderid varchar(40) not null primary key,
    create_time datetime,
    collection_time datetime,
    delivery_time datetime,
    cancel_time datetime,
    status varchar(40),
    cancel_reason varchar(200),
    buyer_email varchar(160),
    payment_method_name varchar(100),
    original_shipping_fee int,
    actual_shipping_fee int,
    shipping_fee_platform_discount int,
    shipping_fee_seller_discount int,
    tracking_number varchar(40),
    shipping_provider varchar(60),
    buyeraddress_lv0 varchar(60),
    buyeraddress_lv1 varchar(60),
    buyeraddress_lv2 varchar(80),
    return_reason varchar(200),
    returned_trackingnumber varchar(50),
    returnstatus varchar(40),
    returnshippingfee_paidbybuyer int,
    returnshippingfee_paidbyplatform int,
    returnshippingfee_paidbyseller int,
    shopname varchar(160),
    dw_updatedat datetime not null
);

create table tiktokorderdetails (
    orderid varchar(40) not null,
    product_skuid varchar(40) not null,
    productid varchar(40),
    productname varchar(255),
    product_skuname varchar(255),
    displayprice int,
    quantity int,
    shopdiscount_allquantities int,
    tiktokdiscount_allquantities int,
    dw_updatedat datetime not null,
    primary key (orderid, product_skuid)
);

create table tiktok_reconciliation (
    order_or_statement_id varchar(40) not null,
    transactiontime date not null,
    transactiontype varchar(40),
    settlement_amount int,
    revenue int,
    subtotal_after_discount int,
    subtotal_before_discount int,
    seller_discount int,
    refund_subtotal_after_discount int,
    refund_subtotal_before_discount int,
    refundforseller_amount int,
    totalfee int,
    dw_updatedat datetime not null,
    primary key (order_or_statement_id, transactiontime)
);

create table dwtable_updatetime_log (
    dwtable_name varchar(160),
    updatetime datetime, -- updatetime show the last time the final record are inserted into the table
    primary key (dwtable_name, updatetime)
);