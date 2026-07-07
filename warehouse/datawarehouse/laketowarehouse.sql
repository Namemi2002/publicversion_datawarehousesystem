-- USING shopeeorders AND shopeeorderdetails TO UPDATE DIM TABLES:
-- create temp_shopeeorders to update dim_order, dim_delivery, dim_customer, dim_reconciliation, dim_product (and fact_orderdetails later)
create temporary table temp_shopeeorders
select s1.orderid,
       s1.createdat,
       s1.orderstatus,
       s1.shopname,
       s1.cancel_reason,
       s1.delivery_orderid,
       s1.courier,
       s1.pickupat,
       s1.completedat,
       s1.buyer_accountname,
       s1.returned_orderids,
       s1.dw_updatedat,
       s2.product_skuid,
       s2.orderproduct_id,
       s2.quantity,
       s2.displayprice,
       s2.realprice,
       s2.shopdiscount_allquantities,
       s2.shopeediscount_allquantities
from shopeeorders s1
left join shopeeorderdetails s2 on s1.orderid = s2.orderid
where s1.dw_updatedat > (select max(updatetime) from dwtable_updatetime_log where dwtable_name = 'shopeeorders');
-- update: dim_order
insert into dim_order (orderid, createdat, status, platform, created_byperson, cancel_reason, return_reason, lastupdateat)
select orderid,
       createdat,
       orderstatus,
       'Shopee shops' as platform,
       shopname,
       cancel_reason,
       returned_orderids,
       dw_updatedat
from temp_shopeeorders
on duplicate key update
    dim_order.createdat = temp_shopeeorders.createdat,
    dim_order.status = temp_shopeeorders.orderstatus,
    dim_order.platform = 'Shopee shops',
    dim_order.created_byperson = temp_shopeeorders.shopname,
    dim_order.cancel_reason = temp_shopeeorders.cancel_reason,
    dim_order.return_reason = temp_shopeeorders.returned_orderids,
    dim_order.lastupdateat = temp_shopeeorders.dw_updatedat;
-- update: dim_delivery
insert into dim_delivery (trackingnumber, courier, delivery_status, createdat, pickupat, deliveryat, lastupdateat)
select delivery_orderid,
       courier,
       orderstatus,
       createdat,
       pickupat,
       completedat,
       dw_updatedat
from temp_shopeeorders
where delivery_orderid is not null
on duplicate key update
    dim_delivery.courier = temp_shopeeorders.courier,
    dim_delivery.delivery_status = temp_shopeeorders.orderstatus,
    dim_delivery.createdat = temp_shopeeorders.createdat,
    dim_delivery.pickupat = temp_shopeeorders.pickupat,
    dim_delivery.deliveryat = temp_shopeeorders.completedat,
    dim_delivery.lastupdateat = temp_shopeeorders.dw_updatedat;
-- update: dim_customer
insert into dim_customer (customer_surrogateid, ecommerce_name)
select coalesce(buyer_accountname, ''), coalesce(buyer_accountname, '')
from temp_shopeeorders
on duplicate key update
    dim_customer.ecommerce_name = coalesce(temp_shopeeorders.buyer_accountname, '');
-- update: dim_reconciliation
insert ignore into dim_reconciliation (order_or_delivery_id)
select orderid
from temp_shopeeorders;
-- update: dim_product (in case a shopee order contains a product id that doesn't exist in internalprice google sheet)
insert into dim_product (productid, retailprice)
select parentproductid, round(avg(realprice)) as avg_retailprice
from
(
select if(locate('-', s.product_skuid)=0, s.product_skuid, left(s.product_skuid, locate('-', s.product_skuid)-1)) as parentproductid,
       s.realprice
from temp_shopeeorders s
left join dim_product p on if(locate('-', s.product_skuid)=0, s.product_skuid, left(s.product_skuid, locate('-', s.product_skuid)-1)) = p.productid
where p.productid is null
) as tb1
group by parentproductid;

-- USING tiktokorders AND tiktokorderdetails TO UPDATE DIM TABLES:
-- create temp_tiktokorders to update dim_order, dim_delivery, dim_customer, dim_reconciliation, dim_product (and fact_orderdetails later)
create temporary table temp_tiktokorders
select t1.orderid,
       t1.create_time,
       t1.status,
       t1.shopname,
       t1.cancel_reason,
       t1.return_reason,
       t1.tracking_number,
       t1.shipping_provider,
       t1.collection_time,
       t1.delivery_time,
       t1.cancel_time,
       t1.buyer_email,
       t1.buyeraddress_lv0,
       t1.buyeraddress_lv1,
       t1.buyeraddress_lv2,
       t1.dw_updatedat,
       t2.product_skuid,
       t2.displayprice,
       t2.quantity,
       t2.shopdiscount_allquantities,
       t2.tiktokdiscount_allquantities
from tiktokorders t1
left join tiktokorderdetails t2 on t1.orderid = t2.orderid
where t1.dw_updatedat > (select max(updatetime) from dwtable_updatetime_log where dwtable_name = 'tiktokorders');
-- update: dim_order
insert into dim_order (orderid, createdat, status, platform, created_byperson, cancel_reason, return_reason, lastupdateat)
select orderid,
       create_time,
       status,
       'Tiktok shops' as platform,
       shopname,
       cancel_reason,
       return_reason,
       dw_updatedat
from temp_tiktokorders
on duplicate key update
    dim_order.createdat = temp_tiktokorders.create_time,
    dim_order.status = temp_tiktokorders.status,
    dim_order.platform = 'Tiktok shops',
    dim_order.created_byperson = temp_tiktokorders.shopname,
    dim_order.cancel_reason = temp_tiktokorders.cancel_reason,
    dim_order.return_reason = temp_tiktokorders.return_reason,
    dim_order.lastupdateat = temp_tiktokorders.dw_updatedat;
-- update: dim_delivery
insert into dim_delivery (trackingnumber, courier, delivery_status, createdat, pickupat, deliveryat, lastupdateat)
select tracking_number,
       shipping_provider,
       status,
       create_time,
       collection_time,
       coalesce(cancel_time, delivery_time) as deliveryat,
       dw_updatedat
from temp_tiktokorders
where tracking_number is not null
on duplicate key update
    dim_delivery.courier = temp_tiktokorders.shipping_provider,
    dim_delivery.delivery_status = temp_tiktokorders.status,
    dim_delivery.createdat = temp_tiktokorders.create_time,
    dim_delivery.pickupat = temp_tiktokorders.collection_time,
    dim_delivery.deliveryat = coalesce(temp_tiktokorders.cancel_time, temp_tiktokorders.delivery_time),
    dim_delivery.lastupdateat = temp_tiktokorders.dw_updatedat;
-- update: dim_customer
insert into dim_customer (customer_surrogateid, ecommerce_name, country, city, district)
select concat(coalesce(buyer_email, ''), '_', coalesce(buyeraddress_lv1, '')) as customer_surrogateid,
       buyer_email,
       buyeraddress_lv0,
       buyeraddress_lv1,
       buyeraddress_lv2
from temp_tiktokorders
on duplicate key update
    dim_customer.ecommerce_name = temp_tiktokorders.buyer_email,
    dim_customer.country = temp_tiktokorders.buyeraddress_lv0,
    dim_customer.city = temp_tiktokorders.buyeraddress_lv1,
    dim_customer.district = temp_tiktokorders.buyeraddress_lv2;
-- update: dim_reconciliation
insert ignore into dim_reconciliation (order_or_delivery_id)
select orderid
from temp_tiktokorders;
-- update: dim_product (in case a tiktok order contains a product id that doesn't exist in internalprice google sheet)
insert into dim_product (productid, retailprice)
select parentproductid,
       round(avg(displayprice - (shopdiscount_allquantities / quantity))) as avg_retailprice
from
(
select if(locate('-', t.product_skuid)=0, t.product_skuid, left(t.product_skuid, locate('-', t.product_skuid)-1)) as parentproductid,
       t.displayprice,
       t.quantity,
       t.shopdiscount_allquantities
from temp_tiktokorders t
left join dim_product p on if(locate('-', t.product_skuid)=0, t.product_skuid, left(t.product_skuid, locate('-', t.product_skuid)-1)) = p.productid
where p.productid is null
) as tb1
group by parentproductid;

-- USING deliveryorders TO UPDATE DIM TABLES:
-- update: dim_delivery
insert into dim_delivery (trackingnumber, courier, courieraccount, delivery_status, createdat, pickupat, deliveryat, lastupdateat)
select delivery_orderid,
       courier,
       courieraccount,
       orderstatus,
       createdat,
       pickupat,
       completedat,
       dw_updatedat
from deliveryorders
where dw_updatedat > (select max(updatetime) from dwtable_updatetime_log where dwtable_name = 'deliveryorders')
on duplicate key update
    dim_delivery.courier = deliveryorders.courier,
    dim_delivery.courieraccount = deliveryorders.courieraccount,
    dim_delivery.delivery_status = deliveryorders.orderstatus,
    dim_delivery.createdat = deliveryorders.createdat,
    dim_delivery.pickupat = deliveryorders.pickupat,
    dim_delivery.deliveryat = deliveryorders.completedat,
    dim_delivery.lastupdateat = deliveryorders.dw_updatedat;
-- update: dim_reconciliation
insert ignore into dim_reconciliation (order_or_delivery_id)
select delivery_orderid
from deliveryorders
where dw_updatedat > (select max(updatetime) from dwtable_updatetime_log where dwtable_name = 'deliveryorders');

-- USING handle_deliveryorders TO UPDATE DIM TABLES:
insert into dim_delivery (trackingnumber, scan_deliveryorder_at, handleteam_note1, handleteam_note2, handleteam_note3)
select delivery_orderid,
       scan_deliveryorder_at,
       handleteam_note1,
       handleteam_note2,
       handleteam_note3
from handle_deliveryorders
where dw_updatedat > (select max(updatetime) from dwtable_updatetime_log where dwtable_name = 'handle_deliveryorders')
on duplicate key update
    dim_delivery.scan_deliveryorder_at = handle_deliveryorders.scan_deliveryorder_at,
    dim_delivery.handleteam_note1 = handle_deliveryorders.handleteam_note1,
    dim_delivery.handleteam_note2 = handle_deliveryorders.handleteam_note2,
    dim_delivery.handleteam_note3 = handle_deliveryorders.handleteam_note3,
    dim_delivery.lastupdateat = handle_deliveryorders.dw_updatedat;

-- USING nhanhvnorders AND nhanhvnorderdetails TO UPDATE DIM TABLES:
-- create temp_nhanhvnorders to update dim_order, dim_customer, dim_reconciliation (and fact_orderdetails later)
create temporary table temp_nhanhvnorders
select n1.orderid,
       n1.created_at,
       n1.orderstatus,
       n1.orderparentsource,
       n1.ordersource,
       n1.platform,
       n1.created_byperson,
       n1.is_wrongproduct,
       n1.customername,
       n1.customerphonenumber,
       n1.customer_cityaddress,
       n1.customer_districtaddress,
       n1.deliverybrand,
       n1.trackingnumber,
       n1.cod_prepaid,
       n1.dw_updatedat,
       ifnull(n2.productid, '') as productid,
       ifnull(n2.parentproductid, '') as parentproductid,
       n2.price,
       n2.quantity,
       n2.discount_allproduct
from nhanhvnorders n1
left join nhanhvnorderdetails n2 on n1.orderid = n2.orderid
where n1.orderstatus not in ('don moi', 'cho khach xac nhan') -- To prevent loading orders with these 2 statuses into data warehouse. Because these orders still can change its productid
      and n1.dw_updatedat > (select max(updatetime) from dwtable_updatetime_log where dwtable_name = 'nhanhvnorders');
update temp_nhanhvnorders
set trackingnumber = concat('TVC_GGSHEET_', orderid)
where deliverybrand = 'Tu Van Chuyen' and trackingnumber is null; -- So it can look up tracking number of 'Tu Van Chuyen' orders
update temp_nhanhvnorders
left join dim_delivery on temp_nhanhvnorders.trackingnumber = dim_delivery.trackingnumber
set temp_nhanhvnorders.trackingnumber = null
where dim_delivery.trackingnumber is null;
-- update: dim_product (in case a nhanhvn order contains a product id that doesn't exist in internalprice google sheet)
insert into dim_product (productid, retailprice)
with addproduct as
(
select ifnull(nh.parentproductid, '') as parentproductid, if(nh.parentproductid is null, null, nh.price) as price, nh.discount_allproduct, nh.quantity
from nhanhvnorderdetails nh
left join dim_product dp on ifnull(nh.parentproductid, '') = dp.productid
where nh.dw_updatedat > (select max(updatetime) from dwtable_updatetime_log where dwtable_name = 'nhanhvnorderdetails') and dp.productid is null
)
select parentproductid,
       round(avg(price - discount_allproduct/quantity)) as retailprice
from addproduct
group by parentproductid;
-- update: dim_order
insert into dim_order (orderid, createdat, status, parentsource, source, platform, created_byperson, is_wrongproduct, lastupdateat)
select orderid,
	   created_at,
       orderstatus,
       orderparentsource,
       ordersource,
       platform,
       created_byperson,
       is_wrongproduct,
       dw_updatedat
from temp_nhanhvnorders
on duplicate key update
	dim_order.createdat = temp_nhanhvnorders.created_at,
    dim_order.status = temp_nhanhvnorders.orderstatus,
    dim_order.parentsource = temp_nhanhvnorders.orderparentsource,
    dim_order.source = temp_nhanhvnorders.ordersource,
    dim_order.platform = temp_nhanhvnorders.platform,
    dim_order.created_byperson = temp_nhanhvnorders.created_byperson,
    dim_order.is_wrongproduct = temp_nhanhvnorders.is_wrongproduct,
    dim_order.lastupdateat = temp_nhanhvnorders.dw_updatedat;
-- update: dim_customer
insert into dim_customer (customer_surrogateid, phonenumber, name, country, city, district)
select concat(coalesce(customerphonenumber, ''), '_', coalesce(customer_cityaddress, '')) as customer_surrogateid,
       customerphonenumber,
       customername,
       'Viet Nam' as country,
       customer_cityaddress,
       customer_districtaddress
from temp_nhanhvnorders
on duplicate key update
    dim_customer.phonenumber = temp_nhanhvnorders.customerphonenumber,
    dim_customer.name = temp_nhanhvnorders.customername,
    dim_customer.country = 'Viet Nam',
    dim_customer.city = temp_nhanhvnorders.customer_cityaddress,
    dim_customer.district = temp_nhanhvnorders.customer_districtaddress;
-- update: dim_reconciliation
insert ignore into dim_reconciliation (order_or_delivery_id)
select trackingnumber
from temp_nhanhvnorders
where trackingnumber is not null;

-- USING delivery_reconciliation TO UPDATE DIM TABLES:
-- create temp_delivery_reconciliation to update dim_reconciliation (and fact_orderdetails later)
create temporary table temp_delivery_reconciliation
select delivery_orderid,
	   max(reconciliation_at) as max_reconciliation_at,
       min(reconciliation_at) as min_reconciliation_at,
       sum(case when reconciliation_value >= 0 then reconciliation_value else null end) as positive_reconciliation_amount,
       sum(case when reconciliation_value < 0 then reconciliation_value else null end) as negative_reconciliation_amount,
       group_concat(reconciliation_at order by reconciliation_at asc separator ',') as all_reconciliation_at,
       group_concat(reconciliation_content order by reconciliation_at asc separator ',') as all_content,
       group_concat(sessionid order by reconciliation_at asc separator ',') as all_sessionid,
       max(dw_updatedat) as max_dw_updatedat
from delivery_reconciliation
group by delivery_orderid
having max(dw_updatedat) > (select max(updatetime) from dwtable_updatetime_log where dwtable_name = 'delivery_reconciliation');
create index idx_delivery_orderid
on temp_delivery_reconciliation(delivery_orderid);
-- update: dim_reconciliation
insert into dim_reconciliation (order_or_delivery_id, max_transactiontime, min_transactiontime, all_sessionid, all_transactiontime, allcontent)
select delivery_orderid,
       max_reconciliation_at,
       min_reconciliation_at,
       all_sessionid,
       all_reconciliation_at,
       all_content
from temp_delivery_reconciliation
on duplicate key update
    dim_reconciliation.max_transactiontime = temp_delivery_reconciliation.max_reconciliation_at,
    dim_reconciliation.min_transactiontime = temp_delivery_reconciliation.min_reconciliation_at,
    dim_reconciliation.all_sessionid = temp_delivery_reconciliation.all_sessionid,
    dim_reconciliation.all_transactiontime = temp_delivery_reconciliation.all_reconciliation_at,
    dim_reconciliation.allcontent = temp_delivery_reconciliation.all_content;

-- USING tiktok_reconciliation TO UPDATE DIM TABLES:
-- create temp_tiktok_reconciliation to update dim_reconciliation (and fact_orderdetails later)
create temporary table temp_tiktok_reconciliation
select order_or_statement_id,
       max(transactiontime) as max_reconciliation_at,
       min(transactiontime) as min_reconciliation_at,
       group_concat(transactiontime order by transactiontime asc separator ',') as all_reconciliation_at,
       sum(revenue) as positive_reconciliation_amount,
       sum(totalfee) as negative_reconciliation_amount,
       max(dw_updatedat) as max_dw_updatedat
from tiktok_reconciliation
group by order_or_statement_id
having max(dw_updatedat) > (select max(updatetime) from dwtable_updatetime_log where dwtable_name = 'tiktok_reconciliation');
create index idx_order_or_statement_id
on temp_tiktok_reconciliation (order_or_statement_id);
-- update: dim_reconciliation
insert into dim_reconciliation (order_or_delivery_id, max_transactiontime, min_transactiontime, all_transactiontime)
select order_or_statement_id,
       max_reconciliation_at,
       min_reconciliation_at,
       all_reconciliation_at
from temp_tiktok_reconciliation
on duplicate key update
    dim_reconciliation.max_transactiontime = temp_tiktok_reconciliation.max_reconciliation_at,
    dim_reconciliation.min_transactiontime = temp_tiktok_reconciliation.min_reconciliation_at,
    dim_reconciliation.all_transactiontime = temp_tiktok_reconciliation.all_reconciliation_at;


-- USING nhanhvnorders AND nhanhvnorderdetails TO UPDATE A FACT TABLE:
-- update: fact_orderdetails
insert into fact_orderdetails (
    orderid,
    productid,
    parentproductid,
    deliveryid,
    customer_surrogateid,
    transaction_orderid,
    baseorder_shippingfee,
    baseorder_cod_collected_allquantity,
    baseorder_codbank_collected_allquantity,
    baseorder_codprepaid_allquantity,
    baseorder_positive_reconciliation_allquantity,
    baseorder_negative_reconciliation_allquantity,
    quantity,
    originalprice,
    discountamount_allquantity,
    extradiscountamount_allquantity,
    return_quantity,
    lastupdateat
)
select orderid,
       productid,
       parentproductid,
       trackingnumber,
       concat(coalesce(customerphonenumber, ''), '_', coalesce(customer_cityaddress, '')) as customer_surrogateid,
       trackingnumber,
       0,
       0,
       0,
       coalesce(cod_prepaid, 0) as cod_prepaid,
       0,
       0,
       coalesce(quantity, 0) as quantity,
       coalesce(price, 0) as price,
       coalesce(discount_allproduct, 0) as discount_allproduct,
       0,
       0,
       dw_updatedat
from temp_nhanhvnorders
on duplicate key update
    fact_orderdetails.parentproductid = temp_nhanhvnorders.parentproductid,
    fact_orderdetails.deliveryid = temp_nhanhvnorders.trackingnumber,
    fact_orderdetails.customer_surrogateid = concat(coalesce(temp_nhanhvnorders.customerphonenumber, ''), '_', coalesce(temp_nhanhvnorders.customer_cityaddress, '')),
    fact_orderdetails.transaction_orderid = temp_nhanhvnorders.trackingnumber,
    fact_orderdetails.baseorder_shippingfee = fact_orderdetails.baseorder_shippingfee,
    fact_orderdetails.baseorder_cod_collected_allquantity = fact_orderdetails.baseorder_cod_collected_allquantity,
    fact_orderdetails.baseorder_codbank_collected_allquantity = fact_orderdetails.baseorder_codbank_collected_allquantity,
    fact_orderdetails.baseorder_codprepaid_allquantity = coalesce(temp_nhanhvnorders.cod_prepaid, 0),
    fact_orderdetails.baseorder_positive_reconciliation_allquantity = fact_orderdetails.baseorder_positive_reconciliation_allquantity,
    fact_orderdetails.baseorder_negative_reconciliation_allquantity = fact_orderdetails.baseorder_negative_reconciliation_allquantity,
    fact_orderdetails.quantity = temp_nhanhvnorders.quantity,
    fact_orderdetails.originalprice = temp_nhanhvnorders.price,
    fact_orderdetails.discountamount_allquantity = temp_nhanhvnorders.discount_allproduct,
    fact_orderdetails.extradiscountamount_allquantity = fact_orderdetails.extradiscountamount_allquantity,
    fact_orderdetails.return_quantity = fact_orderdetails.return_quantity,
    fact_orderdetails.lastupdateat = temp_nhanhvnorders.dw_updatedat;

-- USING shopeeorders AND shopeeorderdetails TO UPDATE A FACT TABLE:
-- update: fact_orderdetails
insert into fact_orderdetails (
    orderid,
    productid,
    parentproductid,
    deliveryid,
    customer_surrogateid,
    transaction_orderid,
    baseorder_shippingfee,
    baseorder_cod_collected_allquantity,
    baseorder_codbank_collected_allquantity,
    baseorder_codprepaid_allquantity,
    baseorder_positive_reconciliation_allquantity,
    baseorder_negative_reconciliation_allquantity,
    quantity,
    originalprice,
    discountamount_allquantity,
    extradiscountamount_allquantity,
    return_quantity,
    lastupdateat
)
select orderid,
       concat(product_skuid, '_', orderproduct_id) as productid,
       if(locate('-', product_skuid)=0, product_skuid, left(product_skuid, locate('-', product_skuid)-1)) as parentproductid,
       delivery_orderid,
       coalesce(buyer_accountname, '') as buyer_accountname,
       orderid,
       0,
       realprice * quantity - shopdiscount_allquantities as baseorder_cod_collected_allquantity, -- grain is a product line in an order
       0,
       0,
       0,
       0,
       quantity,
       displayprice,
       displayprice - realprice as discountamount_allquantity, -- grain is a product line in an order
       shopdiscount_allquantities,
       0,
       dw_updatedat
from temp_shopeeorders
on duplicate key update
    fact_orderdetails.parentproductid = if(locate('-', temp_shopeeorders.product_skuid)=0, temp_shopeeorders.product_skuid, left(temp_shopeeorders.product_skuid, locate('-', temp_shopeeorders.product_skuid)-1)),
    fact_orderdetails.deliveryid = temp_shopeeorders.delivery_orderid,
    fact_orderdetails.customer_surrogateid = coalesce(temp_shopeeorders.buyer_accountname, ''),
    fact_orderdetails.transaction_orderid = temp_shopeeorders.orderid,
    fact_orderdetails.baseorder_shippingfee = fact_orderdetails.baseorder_shippingfee,
    fact_orderdetails.baseorder_cod_collected_allquantity = temp_shopeeorders.realprice * temp_shopeeorders.quantity - temp_shopeeorders.shopdiscount_allquantities,
    fact_orderdetails.baseorder_codbank_collected_allquantity = fact_orderdetails.baseorder_codbank_collected_allquantity,
    fact_orderdetails.baseorder_codprepaid_allquantity = fact_orderdetails.baseorder_codprepaid_allquantity,
    fact_orderdetails.baseorder_positive_reconciliation_allquantity = fact_orderdetails.baseorder_positive_reconciliation_allquantity,
    fact_orderdetails.baseorder_negative_reconciliation_allquantity = fact_orderdetails.baseorder_negative_reconciliation_allquantity,
    fact_orderdetails.quantity = temp_shopeeorders.quantity,
    fact_orderdetails.originalprice = temp_shopeeorders.displayprice,
    fact_orderdetails.discountamount_allquantity = temp_shopeeorders.displayprice - temp_shopeeorders.realprice,
    fact_orderdetails.extradiscountamount_allquantity = temp_shopeeorders.shopdiscount_allquantities,
    fact_orderdetails.return_quantity = fact_orderdetails.return_quantity,
    fact_orderdetails.lastupdateat = temp_shopeeorders.dw_updatedat;

-- USING tiktokorders AND tiktokorderdetails TO UPDATE A FACT TABLE:
-- update: fact_orderdetails
insert into fact_orderdetails (
    orderid,
    productid,
    parentproductid,
    deliveryid,
    customer_surrogateid,
    transaction_orderid,
    baseorder_shippingfee,
    baseorder_cod_collected_allquantity,
    baseorder_codbank_collected_allquantity,
    baseorder_codprepaid_allquantity,
    baseorder_positive_reconciliation_allquantity,
    baseorder_negative_reconciliation_allquantity,
    quantity,
    originalprice,
    discountamount_allquantity,
    extradiscountamount_allquantity,
    return_quantity,
    lastupdateat
    -- tiktok doesn't have extra discount, all posible discount have been added to the shopdiscount_allquantities
)
select orderid,
       product_skuid,
       if(locate('-', product_skuid)=0, product_skuid, left(product_skuid, locate('-', product_skuid)-1)) as parentproductid,
       tracking_number,
       concat(coalesce(buyer_email, ''), '_', coalesce(buyeraddress_lv1, '')) as customer_surrogateid,
       orderid,
       0,
       displayprice * quantity - shopdiscount_allquantities as baseorder_cod_collected_allquantity,
       0,
       0,
       0,
       0,
       quantity,
       displayprice,
       shopdiscount_allquantities,
       0,
       0,
       dw_updatedat
from temp_tiktokorders
on duplicate key update
    fact_orderdetails.parentproductid = if(locate('-', temp_tiktokorders.product_skuid)=0, temp_tiktokorders.product_skuid, left(temp_tiktokorders.product_skuid, locate('-', temp_tiktokorders.product_skuid)-1)),
    fact_orderdetails.deliveryid = temp_tiktokorders.tracking_number,
    fact_orderdetails.customer_surrogateid = concat(coalesce(temp_tiktokorders.buyer_email, ''), '_', coalesce(temp_tiktokorders.buyeraddress_lv1, '')),
    fact_orderdetails.transaction_orderid = temp_tiktokorders.orderid,
    fact_orderdetails.baseorder_shippingfee = fact_orderdetails.baseorder_shippingfee,
    fact_orderdetails.baseorder_cod_collected_allquantity = temp_tiktokorders.displayprice * temp_tiktokorders.quantity - temp_tiktokorders.shopdiscount_allquantities,
    fact_orderdetails.baseorder_codbank_collected_allquantity = fact_orderdetails.baseorder_codbank_collected_allquantity,
    fact_orderdetails.baseorder_codprepaid_allquantity = fact_orderdetails.baseorder_codprepaid_allquantity,
    fact_orderdetails.baseorder_positive_reconciliation_allquantity = fact_orderdetails.baseorder_positive_reconciliation_allquantity,
    fact_orderdetails.baseorder_negative_reconciliation_allquantity = fact_orderdetails.baseorder_negative_reconciliation_allquantity,
    fact_orderdetails.quantity = temp_tiktokorders.quantity,
    fact_orderdetails.originalprice = temp_tiktokorders.displayprice,
    fact_orderdetails.discountamount_allquantity = temp_tiktokorders.shopdiscount_allquantities,
    fact_orderdetails.extradiscountamount_allquantity = fact_orderdetails.extradiscountamount_allquantity,
    fact_orderdetails.return_quantity = fact_orderdetails.return_quantity,
    fact_orderdetails.lastupdateat = temp_tiktokorders.dw_updatedat;

-- USING deliveryorders TO UPDATE A FACT TABLE:
-- update: fact_orderdetails
update fact_orderdetails
inner join deliveryorders on fact_orderdetails.deliveryid = deliveryorders.delivery_orderid
set
fact_orderdetails.baseorder_shippingfee = case
    when deliveryorders.shippingcost is null then fact_orderdetails.baseorder_shippingfee
    when deliveryorders.orderstatus in ('Huy don dat', 'Boi hoan', 'Khong lay duoc hang', 'Don huy', 'Hang that lac', 'Da boi thuong', 'Shop huy lay', 'Da huy giao', 'VTP huy lay', 'Khach hang huy don hang', 'Da huy', 'Huy') then 0 -- canceled orders aren't charged shipping fee
    else deliveryorders.shippingcost
end,
fact_orderdetails.baseorder_cod_collected_allquantity = case
    when deliveryorders.cod_collected is null then fact_orderdetails.baseorder_cod_collected_allquantity
    when deliveryorders.orderstatus not in ('Da doi soat cong no tra hang', 'Hoan hang thanh cong', 'Da hoan hang', 'Da tra', 'Don hoan', 'Da tra ve doi tac', 'Ky nhan 1 phan', 'Chuyen hoan', 'Dang trung chuyen hang hoan', 'Da duyet hoan', 'Dang chuyen hoan', 'Dang tra hang', 'Da tra hang', 'Da ky nhan hoan tra', 'Hoan', 'Da doi soat', 'Da ky nhan', 'Giao hang thanh cong', 'Giao thanh cong', 'Da giao hang', 'Thanh cong', 'Thanh cong 1 phan') then 0 -- if the order have not been delivered to the customer, then set cod_collected equals to 0
    else deliveryorders.cod_collected
end,
fact_orderdetails.lastupdateat = greatest(deliveryorders.dw_updatedat, fact_orderdetails.lastupdateat);

-- USING customerbanks TO UPDATE A FACT TABLE:
-- update: fact_orderdetails
with bank as
(
select orderid, sum(bankvalue) as bankvalue, max(dw_updatedat) as max_dw_updatedat
from customerbanks
group by orderid
)
update fact_orderdetails
inner join bank on fact_orderdetails.orderid = bank.orderid
set fact_orderdetails.baseorder_codbank_collected_allquantity = coalesce(bank.bankvalue, fact_orderdetails.baseorder_codbank_collected_allquantity),
    fact_orderdetails.lastupdateat = greatest(bank.max_dw_updatedat, fact_orderdetails.lastupdateat);

-- USING delivery_reconciliation TO UPDATE A FACT TABLE:
-- update: fact_orderdetails
update fact_orderdetails
inner join temp_delivery_reconciliation on fact_orderdetails.transaction_orderid = temp_delivery_reconciliation.delivery_orderid
set fact_orderdetails.baseorder_positive_reconciliation_allquantity = coalesce(temp_delivery_reconciliation.positive_reconciliation_amount, fact_orderdetails.baseorder_positive_reconciliation_allquantity),
    fact_orderdetails.baseorder_negative_reconciliation_allquantity = coalesce(temp_delivery_reconciliation.negative_reconciliation_amount, fact_orderdetails.baseorder_negative_reconciliation_allquantity),
    fact_orderdetails.lastupdateat = greatest(temp_delivery_reconciliation.max_dw_updatedat, fact_orderdetails.lastupdateat);

-- USING tiktok_reconciliation TO UPDATE A FACT TABLE:
-- update: fact_orderdetails
update fact_orderdetails
inner join temp_tiktok_reconciliation on fact_orderdetails.transaction_orderid = temp_tiktok_reconciliation.order_or_statement_id
set fact_orderdetails.baseorder_positive_reconciliation_allquantity = coalesce(temp_tiktok_reconciliation.positive_reconciliation_amount, fact_orderdetails.baseorder_positive_reconciliation_allquantity),
    fact_orderdetails.baseorder_negative_reconciliation_allquantity = coalesce(temp_tiktok_reconciliation.negative_reconciliation_amount, fact_orderdetails.baseorder_negative_reconciliation_allquantity),
    fact_orderdetails.lastupdateat = greatest(temp_tiktok_reconciliation.max_dw_updatedat, fact_orderdetails.lastupdateat);

-- USING returnedorders_scan TO UPDATE A FACT TABLE:
-- update: fact_orderdetails
with returnedorders as
(
select delivery_orderid,
       productid,
       count(productid) as returnednumber,
       max(dw_updatedat) as max_dw_updatedat
from returnedorders_scan
group by delivery_orderid, productid
)
update fact_orderdetails
inner join returnedorders on fact_orderdetails.deliveryid = returnedorders.delivery_orderid
                         and if(locate('_', fact_orderdetails.productid)=0, fact_orderdetails.productid, left(fact_orderdetails.productid, locate('_', fact_orderdetails.productid)-1)) = returnedorders.productid
set fact_orderdetails.return_quantity = coalesce(returnedorders.returnednumber, fact_orderdetails.return_quantity),
    fact_orderdetails.lastupdateat = greatest(returnedorders.max_dw_updatedat, fact_orderdetails.lastupdateat);

-- CALCULATE NECESSARY COLUMNS IN THE FACT TABLE:
-- calculate the finalstatus column:
create temporary table temp_fact_totalorderquantity
select orderid,
       sum(quantity) as totalquantity,
       sum(quantity * originalprice - discountamount_allquantity - extradiscountamount_allquantity) as totalordercodamount -- The COD amount when creating an order
from fact_orderdetails
group by orderid;
create index idx_orderid
on temp_fact_totalorderquantity(orderid);
update fact_orderdetails f
left join dim_order do on f.orderid = do.orderid
left join dim_delivery dd on f.deliveryid = dd.trackingnumber
left join temp_fact_totalorderquantity t on f.orderid = t.orderid
set finalstatus = case
    when do.parentsource not in ('don doi', 'bo sung') and dd.courier <> 'Tu Van Chuyen' and dd.delivery_status in ('Da doi soat cong no tra hang', 'Hoan hang thanh cong', 'Da hoan hang', 'Da tra', 'Don hoan', 'Da tra ve doi tac', 'Ky nhan 1 phan', 'Chuyen hoan', 'Dang trung chuyen hang hoan', 'Da duyet hoan', 'Dang chuyen hoan', 'Dang tra hang', 'Da tra hang', 'Da ky nhan hoan tra', 'Ky nhan chuyen hoan', 'Da doi soat', 'Da ky nhan', 'Giao hang thanh cong', 'Giao thanh cong', 'Da giao hang') and f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) <= 0 then 'Hoan'
    when do.parentsource not in ('don doi', 'bo sung') and dd.courier <> 'Tu Van Chuyen' and dd.delivery_status in ('Da doi soat cong no tra hang', 'Hoan hang thanh cong', 'Da hoan hang', 'Da tra', 'Don hoan', 'Da tra ve doi tac', 'Ky nhan 1 phan', 'Chuyen hoan', 'Dang trung chuyen hang hoan', 'Da duyet hoan', 'Dang chuyen hoan', 'Dang tra hang', 'Da tra hang', 'Da ky nhan hoan tra', 'Ky nhan chuyen hoan', 'Da doi soat', 'Da ky nhan', 'Giao hang thanh cong', 'Giao thanh cong', 'Da giao hang') and (f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) > 0 and f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) <= 30000) then 'Hoan thu ship'
    when do.parentsource not in ('don doi', 'bo sung') and dd.courier <> 'Tu Van Chuyen' and dd.delivery_status in ('Da doi soat cong no tra hang', 'Hoan hang thanh cong', 'Da hoan hang', 'Da tra', 'Don hoan', 'Da tra ve doi tac', 'Ky nhan 1 phan', 'Chuyen hoan', 'Dang trung chuyen hang hoan', 'Da duyet hoan', 'Dang chuyen hoan', 'Dang tra hang', 'Da tra hang', 'Da ky nhan hoan tra', 'Ky nhan chuyen hoan') and f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) >= t.totalordercodamount then 'Hoan'
    when do.parentsource not in ('don doi', 'bo sung') and dd.courier <> 'Tu Van Chuyen' and dd.delivery_status in ('Da doi soat', 'Da ky nhan', 'Giao hang thanh cong', 'Giao thanh cong', 'Da giao hang') and f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) >= t.totalordercodamount then 'Thanh cong'
    when do.parentsource not in ('don doi', 'bo sung') and dd.courier <> 'Tu Van Chuyen' and dd.delivery_status in ('Da doi soat cong no tra hang', 'Hoan hang thanh cong', 'Da hoan hang', 'Da tra', 'Don hoan', 'Da tra ve doi tac', 'Ky nhan 1 phan', 'Chuyen hoan', 'Dang trung chuyen hang hoan', 'Da duyet hoan', 'Dang chuyen hoan', 'Dang tra hang', 'Da tra hang', 'Da ky nhan hoan tra', 'Ky nhan chuyen hoan', 'Da doi soat', 'Da ky nhan', 'Giao hang thanh cong', 'Giao thanh cong', 'Da giao hang') and (f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) > 30000 and f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) < t.totalordercodamount) and f.return_quantity=0 then 'Thanh cong'
    when do.parentsource not in ('don doi', 'bo sung') and dd.courier <> 'Tu Van Chuyen' and dd.delivery_status in ('Da doi soat cong no tra hang', 'Hoan hang thanh cong', 'Da hoan hang', 'Da tra', 'Don hoan', 'Da tra ve doi tac', 'Ky nhan 1 phan', 'Chuyen hoan', 'Dang trung chuyen hang hoan', 'Da duyet hoan', 'Dang chuyen hoan', 'Dang tra hang', 'Da tra hang', 'Da ky nhan hoan tra', 'Ky nhan chuyen hoan', 'Da doi soat', 'Da ky nhan', 'Giao hang thanh cong', 'Giao thanh cong', 'Da giao hang') and (f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) > 30000 and f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) < t.totalordercodamount) and f.return_quantity >= f.quantity then 'Hoan'
    when do.parentsource not in ('don doi', 'bo sung') and dd.courier <> 'Tu Van Chuyen' and dd.delivery_status in ('Da doi soat cong no tra hang', 'Hoan hang thanh cong', 'Da hoan hang', 'Da tra', 'Don hoan', 'Da tra ve doi tac', 'Ky nhan 1 phan', 'Chuyen hoan', 'Dang trung chuyen hang hoan', 'Da duyet hoan', 'Dang chuyen hoan', 'Dang tra hang', 'Da tra hang', 'Da ky nhan hoan tra', 'Ky nhan chuyen hoan', 'Da doi soat', 'Da ky nhan', 'Giao hang thanh cong', 'Giao thanh cong', 'Da giao hang') and (f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) > 30000 and f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) < t.totalordercodamount) and (f.return_quantity > 0 and f.return_quantity < f.quantity) then 'Hoan mot phan'
    when do.parentsource = 'bo sung' and dd.courier <> 'Tu Van Chuyen' and dd.delivery_status in ('Da doi soat cong no tra hang', 'Hoan hang thanh cong', 'Da hoan hang', 'Da tra', 'Don hoan', 'Da tra ve doi tac', 'Ky nhan 1 phan', 'Chuyen hoan', 'Dang trung chuyen hang hoan', 'Da duyet hoan', 'Dang chuyen hoan', 'Dang tra hang', 'Da tra hang', 'Da ky nhan hoan tra', 'Ky nhan chuyen hoan', 'Da doi soat', 'Da ky nhan', 'Giao hang thanh cong', 'Giao thanh cong', 'Da giao hang') then 'Thanh cong'
    when do.parentsource = 'don doi' and dd.courier <> 'Tu Van Chuyen' and dd.delivery_status in ('Da doi soat cong no tra hang', 'Hoan hang thanh cong', 'Da hoan hang', 'Da tra', 'Don hoan', 'Da tra ve doi tac', 'Ky nhan 1 phan', 'Chuyen hoan', 'Dang trung chuyen hang hoan', 'Da duyet hoan', 'Dang chuyen hoan', 'Dang tra hang', 'Da tra hang', 'Da ky nhan hoan tra', 'Ky nhan chuyen hoan', 'Da doi soat', 'Da ky nhan', 'Giao hang thanh cong', 'Giao thanh cong', 'Da giao hang') and (f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) <= 0) then 'Hoan'
    when do.parentsource = 'don doi' and dd.courier <> 'Tu Van Chuyen' and dd.delivery_status in ('Da doi soat cong no tra hang', 'Hoan hang thanh cong', 'Da hoan hang', 'Da tra', 'Don hoan', 'Da tra ve doi tac', 'Ky nhan 1 phan', 'Chuyen hoan', 'Dang trung chuyen hang hoan', 'Da duyet hoan', 'Dang chuyen hoan', 'Dang tra hang', 'Da tra hang', 'Da ky nhan hoan tra', 'Ky nhan chuyen hoan', 'Da doi soat', 'Da ky nhan', 'Giao hang thanh cong', 'Giao thanh cong', 'Da giao hang') and (f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) > 0 and f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) <= 30000) then 'Hoan thu ship'
    when do.parentsource = 'don doi' and dd.courier <> 'Tu Van Chuyen' and dd.delivery_status in ('Da doi soat cong no tra hang', 'Hoan hang thanh cong', 'Da hoan hang', 'Da tra', 'Don hoan', 'Da tra ve doi tac', 'Ky nhan 1 phan', 'Chuyen hoan', 'Dang trung chuyen hang hoan', 'Da duyet hoan', 'Dang chuyen hoan', 'Dang tra hang', 'Da tra hang', 'Da ky nhan hoan tra', 'Ky nhan chuyen hoan', 'Da doi soat', 'Da ky nhan', 'Giao hang thanh cong', 'Giao thanh cong', 'Da giao hang') and (f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) > 30000) then 'Hoan mot phan'
    when dd.courier <> 'Tu Van Chuyen' and dd.delivery_status in ('Huy don dat', 'Boi hoan', 'Khong lay duoc hang', 'Don huy', 'Hang that lac', 'Da boi thuong', 'Shop huy lay', 'Da huy giao', 'VTP huy lay', 'Khach hang huy don hang', 'Da huy', 'Huy', 'CANCELLED') then 'Huy'
    when do.parentsource not in ('don doi', 'bo sung') and (dd.courier = 'Tu Van Chuyen' or dd.courier is null) and do.status in ('thanh cong', 'xac nhan hoan', 'dang chuyen hoan', 'da chuyen hoan', 'da hoan') and f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) <= 0 then 'Hoan'
    when do.parentsource not in ('don doi', 'bo sung') and (dd.courier = 'Tu Van Chuyen' or dd.courier is null) and do.status in ('thanh cong', 'xac nhan hoan', 'dang chuyen hoan', 'da chuyen hoan', 'da hoan') and (f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) > 0 and f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) <= 30000) then 'Hoan thu ship'
    when do.parentsource not in ('don doi', 'bo sung') and (dd.courier = 'Tu Van Chuyen' or dd.courier is null) and do.status in ('thanh cong', 'xac nhan hoan', 'dang chuyen hoan', 'da chuyen hoan', 'da hoan') and (f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) >= t.totalordercodamount) then 'Thanh cong'
    when do.parentsource not in ('don doi', 'bo sung') and (dd.courier = 'Tu Van Chuyen' or dd.courier is null) and do.status in ('thanh cong', 'xac nhan hoan', 'dang chuyen hoan', 'da chuyen hoan', 'da hoan') and (f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) > 30000 and f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) < t.totalordercodamount) and f.return_quantity = 0 then 'Thanh cong'
    when do.parentsource not in ('don doi', 'bo sung') and (dd.courier = 'Tu Van Chuyen' or dd.courier is null) and do.status in ('thanh cong', 'xac nhan hoan', 'dang chuyen hoan', 'da chuyen hoan', 'da hoan') and (f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) > 30000 and f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) < t.totalordercodamount) and f.return_quantity >= f.quantity then 'Hoan'
    when do.parentsource not in ('don doi', 'bo sung') and (dd.courier = 'Tu Van Chuyen' or dd.courier is null) and do.status in ('thanh cong', 'xac nhan hoan', 'dang chuyen hoan', 'da chuyen hoan', 'da hoan') and (f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) > 30000 and f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) < t.totalordercodamount) and (f.return_quantity > 0 and f.return_quantity < f.quantity) then 'Hoan mot phan'
    when do.parentsource = 'bo sung' and (dd.courier = 'Tu Van Chuyen' or dd.courier is null) and do.status in ('thanh cong', 'xac nhan hoan', 'dang chuyen hoan', 'da chuyen hoan', 'da hoan') then 'Thanh cong'
    when do.parentsource = 'don doi' and (dd.courier = 'Tu Van Chuyen' or dd.courier is null) and do.status in ('thanh cong', 'xac nhan hoan', 'dang chuyen hoan', 'da chuyen hoan', 'da hoan') and (f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) <= 0) then 'Hoan'
    when do.parentsource = 'don doi' and (dd.courier = 'Tu Van Chuyen' or dd.courier is null) and do.status in ('thanh cong', 'xac nhan hoan', 'dang chuyen hoan', 'da chuyen hoan', 'da hoan') and (f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) > 0 and f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) <= 30000) then 'Hoan thu ship'
    when do.parentsource = 'don doi' and (dd.courier = 'Tu Van Chuyen' or dd.courier is null) and do.status in ('thanh cong', 'xac nhan hoan', 'dang chuyen hoan', 'da chuyen hoan', 'da hoan') and (f.baseorder_cod_collected_allquantity + if(f.baseorder_codbank_collected_allquantity=0, f.baseorder_codprepaid_allquantity, f.baseorder_codbank_collected_allquantity) > 30000) then 'Hoan thu ship'
    when (dd.courier = 'Tu Van Chuyen' or dd.courier is null) and do.status in ('hang van chuyen huy don', 'khach huy', 'he thong huy') then 'Huy'
    when do.parentsource is null and dd.delivery_status = 'COMPLETED' and do.return_reason is null then 'Thanh cong'
    when do.parentsource is null and dd.delivery_status = 'COMPLETED' and do.return_reason is not null and t.totalquantity = 1 then 'Hoan'
    when do.parentsource is null and dd.delivery_status = 'COMPLETED' and do.return_reason is not null and t.totalquantity > 1 and f.return_quantity >= f.quantity then 'Hoan'
    when do.parentsource is null and dd.delivery_status = 'COMPLETED' and do.return_reason is not null and t.totalquantity > 1 and (f.return_quantity > 0 and f.return_quantity < f.quantity) then 'Hoan mot phan'
    when do.parentsource is null and dd.delivery_status = 'COMPLETED' and do.return_reason is not null and t.totalquantity > 1 and f.return_quantity = 0 then 'Thanh cong'
    when do.parentsource is null and (do.status= 'CANCELLED' or dd.delivery_status = 'CANCELLED') then 'Huy'
    else 'Pending'
end
where f.lastupdateat > (select max(updatetime) from dwtable_updatetime_log where dwtable_name = 'fact and dim tables');
-- calculate shippingfee, negative_reconciliation_allquantity columns:
update fact_orderdetails f
left join temp_fact_totalorderquantity t on f.orderid = t.orderid
set f.shippingfee = f.baseorder_shippingfee * if(t.totalquantity=0, 0, f.quantity / t.totalquantity), -- t.totalquantity is never null because temp_fact_totalorderquantity results directly from fact_orderdetails
    f.negative_reconciliation_allquantity = f.baseorder_negative_reconciliation_allquantity * if(t.totalquantity=0, 0, f.quantity / t.totalquantity)
where f.lastupdateat > (select max(updatetime) from dwtable_updatetime_log where dwtable_name = 'fact and dim tables');
-- calculate cod_collected_allquantity, codbank_collected_allquantity, positive_reconciliation_allquantity columns:
create temporary table temp_fact_successcodamountatcreated
select orderid,
       productid,
       case
        when finalstatus in ('Huy', 'Pending', 'Hoan') then 0
        when finalstatus in ('Thanh cong', 'Hoan thu ship') then quantity * originalprice - discountamount_allquantity - extradiscountamount_allquantity
        when finalstatus = 'Hoan mot phan' and quantity > return_quantity then (quantity - return_quantity) * originalprice - (discountamount_allquantity * if(quantity=0, 0, (quantity - return_quantity) / quantity)) - (extradiscountamount_allquantity * if(quantity=0, 0, (quantity - return_quantity) / quantity))
        when finalstatus = 'Hoan mot phan' and quantity <= return_quantity then 0
       end as success_codamount_atcreated, -- For Shopee & Tiktok orders, this metric already showed the cod collected for each product line in the order
       sum(case
        when finalstatus in ('Huy', 'Pending', 'Hoan') then 0
        when finalstatus in ('Thanh cong', 'Hoan thu ship') then quantity * originalprice - discountamount_allquantity - extradiscountamount_allquantity
        when finalstatus = 'Hoan mot phan' and quantity > return_quantity then (quantity - return_quantity) * originalprice - (discountamount_allquantity * if(quantity=0, 0, (quantity - return_quantity) / quantity)) - (extradiscountamount_allquantity * if(quantity=0, 0, (quantity - return_quantity) / quantity))
        when finalstatus = 'Hoan mot phan' and quantity <= return_quantity then 0
       end) over(partition by orderid) as totalorder_success_codamount_atcreated,
       quantity * originalprice - discountamount_allquantity - extradiscountamount_allquantity as codamount_atcreated,
       sum(quantity * originalprice - discountamount_allquantity - extradiscountamount_allquantity) over(partition by orderid) as totalorder_codamount_atcreated
from fact_orderdetails;
create index idx_orderid_productid
on temp_fact_successcodamountatcreated(orderid, productid);
update fact_orderdetails f
left join temp_fact_successcodamountatcreated t on f.orderid = t.orderid and f.productid = t.productid
left join dim_order do on f.orderid = do.orderid
left join dim_delivery dd on f.deliveryid = dd.trackingnumber
set
    f.cod_collected_allquantity = case
            when do.platform not in ('Shopee shops', 'Tiktok shops') then f.baseorder_cod_collected_allquantity * if(t.totalorder_success_codamount_atcreated=0, 0, t.success_codamount_atcreated / t.totalorder_success_codamount_atcreated)
            else t.success_codamount_atcreated
        end,
    f.codbank_collected_allquantity = f.baseorder_codbank_collected_allquantity * if(t.totalorder_success_codamount_atcreated=0, 0, t.success_codamount_atcreated / t.totalorder_success_codamount_atcreated),
    f.positive_reconciliation_allquantity = f.baseorder_positive_reconciliation_allquantity * if(t.totalorder_success_codamount_atcreated=0, 0, t.success_codamount_atcreated / t.totalorder_success_codamount_atcreated),
    f.codprepaid_allquantity = f.baseorder_codprepaid_allquantity * if(t.totalorder_codamount_atcreated=0, 0, t.codamount_atcreated / t.totalorder_codamount_atcreated)
where f.lastupdateat > (select max(updatetime) from dwtable_updatetime_log where dwtable_name = 'fact and dim tables');
-- If an order has 'Huy' or 'Pending' status, but still receives money from reconciliation, dividing that money for all product lines in the order:
update fact_orderdetails f
left join temp_fact_totalorderquantity t on f.orderid = t.orderid
set f.positive_reconciliation_allquantity = f.baseorder_positive_reconciliation_allquantity * if(t.totalquantity=0, 0, f.quantity / t.totalquantity)
where f.finalstatus in ('Huy', 'Pending') and f.lastupdateat > (select max(updatetime) from dwtable_updatetime_log where dwtable_name = 'fact and dim tables');


-- UPDATE THE dwtable_updatetime_log TABLE:
insert ignore into dwtable_updatetime_log(dwtable_name, updatetime)
select 'nhanhvnorders', max(dw_updatedat)
from nhanhvnorders;
insert ignore into dwtable_updatetime_log(dwtable_name, updatetime)
select 'nhanhvnorderdetails', max(dw_updatedat)
from nhanhvnorderdetails;
insert ignore into dwtable_updatetime_log(dwtable_name, updatetime)
select 'deliveryorders', max(dw_updatedat)
from deliveryorders;
insert ignore into dwtable_updatetime_log(dwtable_name, updatetime)
select 'customerbanks', max(dw_updatedat)
from customerbanks;
insert ignore into dwtable_updatetime_log(dwtable_name, updatetime)
select 'returnedorders_scan', max(dw_updatedat)
from returnedorders_scan;
insert ignore into dwtable_updatetime_log(dwtable_name, updatetime)
select 'delivery_reconciliation', max(dw_updatedat)
from delivery_reconciliation;
insert ignore into dwtable_updatetime_log(dwtable_name, updatetime)
select 'handle_deliveryorders', max(dw_updatedat)
from handle_deliveryorders;
insert ignore into dwtable_updatetime_log(dwtable_name, updatetime)
select 'shopeeorders', max(dw_updatedat)
from shopeeorders;
insert ignore into dwtable_updatetime_log(dwtable_name, updatetime)
select 'shopeeorderdetails', max(dw_updatedat)
from shopeeorderdetails;
insert ignore into dwtable_updatetime_log(dwtable_name, updatetime)
select 'tiktokorders', max(dw_updatedat)
from tiktokorders;
insert ignore into dwtable_updatetime_log(dwtable_name, updatetime)
select 'tiktokorderdetails', max(dw_updatedat)
from tiktokorderdetails;
insert ignore into dwtable_updatetime_log(dwtable_name, updatetime)
select 'tiktok_reconciliation', max(dw_updatedat)
from tiktok_reconciliation;
insert ignore into dwtable_updatetime_log(dwtable_name, updatetime)
select 'fact and dim tables', max(lastupdateat)
from fact_orderdetails;