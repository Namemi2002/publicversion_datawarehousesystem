-- DATA WAREHOUSE TABLES:

create table dim_order (
    orderid varchar(40) not null primary key,
    createdat datetime,
    status varchar(60),
    parentsource varchar(40),
    source varchar(100),
    platform varchar(60),
    created_byperson varchar(60),
    cancel_reason varchar(255),
    return_reason varchar(255),
    is_wrongproduct boolean,
    lastupdateat datetime
);

create table dim_delivery (
    trackingnumber varchar(40) not null primary key,
    courier varchar(40),
    courieraccount varchar(40),
    delivery_status varchar(60),
    createdat datetime,
    pickupat datetime,
    deliveryat datetime,
    scan_deliveryorder_at date,
    handleteam_note1 varchar(255),
    handleteam_note2 varchar(255),
    handleteam_note3 varchar(255),
    lastupdateat datetime
);

create table dim_customer (
    customer_surrogateid varchar(160) not null primary key, -- created by concat phonenumber & ecommerce_name & city
    phonenumber varchar(40),
    name varchar(200),
    ecommerce_name varchar(60),
    country varchar(60),
    city varchar(60),
    district varchar(80)
);

create table dim_product (
    productid varchar(40) not null primary key,
    retailprice int,
    cate_purpose varchar(60),
    cate_color varchar(60),
    cate_fabric varchar(60),
    cate_collar varchar(60),
    cate_sleeve varchar(60),
    cate_sleevelong varchar(60),
    cate_dresstype varchar(60),
    cate_fabricpattern varchar(60)
);

create table dim_reconciliation (
    order_or_delivery_id varchar(160) not null primary key, -- grouped by delivery_orderid
    max_transactiontime datetime,
    min_transactiontime datetime,
    all_sessionid varchar(255),
    all_transactiontime varchar(255),
    allcontent varchar(255)
);

create table fact_orderdetails (
    orderid varchar(40) not null,
    productid varchar(40) not null,
    parentproductid varchar(40) not null,
    deliveryid varchar(40),
    customer_surrogateid varchar(160) not null,
    transaction_orderid varchar(40),
    baseorder_shippingfee int, -- this metrics is the grain for an order, need to calculate for the (order, product) grain later
    baseorder_cod_collected_allquantity int, -- this metrics is the grain for an order, need to calculate for the (order, product) grain later
    baseorder_codbank_collected_allquantity int, -- this metrics is the grain for an order, need to calculate for the (order, product) grain later
    baseorder_codprepaid_allquantity int, -- this metrics is the grain for an order, need to calculate for the (order, product) grain later
    baseorder_positive_reconciliation_allquantity int, -- this metrics is the grain for an order, need to calculate for the (order, product) grain later
    baseorder_negative_reconciliation_allquantity int, -- this metrics is the grain for an order, need to calculate for the (order, product) grain later
    shippingfee decimal(25,10),
    quantity int,
    originalprice int,
    discountamount_allquantity int,
    extradiscountamount_allquantity decimal(25,10),
    cod_collected_allquantity decimal(25,10), -- cod_collected is the amount that delivery has collected from customer (Nhanhvn orders) or the amount that showed in tiktok/shopeeorderdetails table (e-commerce orders)
    codbank_collected_allquantity decimal(25,10), -- codbank_collected only counts on Nhanhvn orders
    codprepaid_allquantity decimal(25,10), -- codprepaid only counts on Nhanhvn orders
    return_quantity int,
    positive_reconciliation_allquantity decimal(25,10),
    negative_reconciliation_allquantity decimal(25,10),
    finalstatus varchar(40),
    lastupdateat datetime,
    primary key (orderid, productid),
    constraint fk_order foreign key (orderid) references dim_order(orderid),
    constraint fk_delivery foreign key (deliveryid) references dim_delivery(trackingnumber),
    constraint fk_customer foreign key (customer_surrogateid) references dim_customer(customer_surrogateid),
    constraint fk_product foreign key (parentproductid) references dim_product(productid),
    constraint fk_reconciliation foreign key (transaction_orderid) references dim_reconciliation(order_or_delivery_id)
);