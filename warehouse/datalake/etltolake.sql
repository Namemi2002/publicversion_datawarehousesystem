-- IMPORTANT REMINDER: ALL QUERY IN THIS FILE MUST START WITH "--name: table_name"
--name: nhanhvnorders
insert into nhanhvnorders
values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
as new
on duplicate key update
    nhanhvnorders.created_at = new.created_at,
    nhanhvnorders.customername = new.customername,
    nhanhvnorders.customerphonenumber = new.customerphonenumber,
    nhanhvnorders.customer_cityaddress = new.customer_cityaddress,
    nhanhvnorders.customer_districtaddress = new.customer_districtaddress,
    nhanhvnorders.deliverybrand = new.deliverybrand,
    nhanhvnorders.trackingnumber = new.trackingnumber,
    nhanhvnorders.orderstatus = new.orderstatus,
    nhanhvnorders.orderparentsource = new.orderparentsource,
    nhanhvnorders.ordersource = new.ordersource,
    nhanhvnorders.platform = new.platform,
    nhanhvnorders.senddelivery_at = new.senddelivery_at,
    nhanhvnorders.cod_prepaid = new.cod_prepaid,
    nhanhvnorders.created_byperson = new.created_byperson,
    nhanhvnorders.internalnote = new.internalnote,
    nhanhvnorders.customernote = new.customernote,
    nhanhvnorders.previousid_internalnote = new.previousid_internalnote,
    nhanhvnorders.previousid_customernote = new.previousid_customernote,
    nhanhvnorders.is_wrongproduct = new.is_wrongproduct,
    nhanhvnorders.dw_updatedat = new.dw_updatedat;

--name: nhanhvnorderdetails
insert into nhanhvnorderdetails
values (%s,%s,%s,%s,%s,%s,%s,%s)
as new
on duplicate key update
    nhanhvnorderdetails.productbarcode = new.productbarcode,
    nhanhvnorderdetails.parentproductid = new.parentproductid,
    nhanhvnorderdetails.price = new.price,
    nhanhvnorderdetails.discount_allproduct = new.discount_allproduct,
    nhanhvnorderdetails.quantity = new.quantity,
    nhanhvnorderdetails.dw_updatedat = new.dw_updatedat;

--name: deliveryorders
insert into deliveryorders
values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
as new
on duplicate key update
    dw_updatedat = IF(
        NOT (deliveryorders.shop_orderid <=> new.shop_orderid)
        OR NOT (deliveryorders.orderstatus <=> new.orderstatus)
        OR NOT (deliveryorders.cod_collected <=> new.cod_collected)
        OR NOT (deliveryorders.cod_declared <=> new.cod_declared)
        OR NOT (deliveryorders.shippingcost <=> new.shippingcost)
        OR NOT (deliveryorders.createdat <=> new.createdat)
        OR NOT (deliveryorders.pickupat <=> new.pickupat)
        OR NOT (deliveryorders.completedat <=> new.completedat)
        OR NOT (deliveryorders.courier <=> new.courier)
        OR NOT (deliveryorders.compensationvalue <=> new.compensationvalue)
        OR NOT (deliveryorders.courieraccount <=> new.courieraccount),
        new.dw_updatedat,
        deliveryorders.dw_updatedat
    ),
    deliveryorders.shop_orderid = new.shop_orderid,
    deliveryorders.orderstatus = new.orderstatus,
    deliveryorders.cod_collected = new.cod_collected,
    deliveryorders.cod_declared = new.cod_declared,
    deliveryorders.shippingcost = new.shippingcost,
    deliveryorders.createdat = new.createdat,
    deliveryorders.pickupat = new.pickupat,
    deliveryorders.completedat = new.completedat,
    deliveryorders.courier = new.courier,
    deliveryorders.compensationvalue = new.compensationvalue,
    deliveryorders.courieraccount = new.courieraccount;

--name: customerbanks
insert into customerbanks
values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
as new
on duplicate key update
    customerbanks.dw_updatedat = IF(
        NOT (customerbanks.notedate <=> new.notedate)
        OR NOT (customerbanks.orderid <=> new.orderid)
        OR NOT (customerbanks.customerphonenumber <=> new.customerphonenumber)
        OR NOT (customerbanks.bankvalue <=> new.bankvalue)
        OR NOT (customerbanks.verifybyperson <=> new.verifybyperson)
        OR NOT (customerbanks.ftcode <=> new.ftcode)
        OR NOT (customerbanks.note <=> new.note),
        new.dw_updatedat,
        customerbanks.dw_updatedat
    ),
    customerbanks.notedate = new.notedate,
    customerbanks.orderid = new.orderid,
    customerbanks.customerphonenumber = new.customerphonenumber,
    customerbanks.bankvalue = new.bankvalue,
    customerbanks.verifybyperson = new.verifybyperson,
    customerbanks.ftcode = new.ftcode,
    customerbanks.note = new.note;

--name: returnedorders_scan
insert into returnedorders_scan
values (%s,%s,%s,%s,%s)
as new
on duplicate key update
    returnedorders_scan.dw_updatedat = IF(
        NOT (returnedorders_scan.scanat <=> new.scanat)
        OR NOT (returnedorders_scan.delivery_orderid <=> new.delivery_orderid)
        OR NOT (returnedorders_scan.productid <=> new.productid),
        new.dw_updatedat,
        returnedorders_scan.dw_updatedat
    ),
    returnedorders_scan.scanat = new.scanat,
    returnedorders_scan.delivery_orderid = new.delivery_orderid,
    returnedorders_scan.productid = new.productid;

--name: delivery_reconciliation
insert into delivery_reconciliation
values (%s,%s,%s,%s,%s,%s,%s)
as new
on duplicate key update
    delivery_reconciliation.dw_updatedat = IF(
        NOT (delivery_reconciliation.reconciliation_value <=> new.reconciliation_value)
        OR NOT (delivery_reconciliation.reconciliation_at <=> new.reconciliation_at)
        OR NOT (delivery_reconciliation.courier <=> new.courier)
        OR NOT (delivery_reconciliation.reconciliation_content <=> new.reconciliation_content),
        new.dw_updatedat,
        delivery_reconciliation.dw_updatedat
    ),
    delivery_reconciliation.reconciliation_value = new.reconciliation_value,
    delivery_reconciliation.reconciliation_at = new.reconciliation_at,
    delivery_reconciliation.courier = new.courier,
    delivery_reconciliation.reconciliation_content = new.reconciliation_content;

--name: handle_deliveryorders
insert into handle_deliveryorders
values (%s,%s,%s,%s,%s,%s)
as new
on duplicate key update
    handle_deliveryorders.dw_updatedat = IF(
        NOT (handle_deliveryorders.scan_deliveryorder_at <=> new.scan_deliveryorder_at)
        OR NOT (handle_deliveryorders.handleteam_note1 <=> new.handleteam_note1)
        OR NOT (handle_deliveryorders.handleteam_note2 <=> new.handleteam_note2)
        OR NOT (handle_deliveryorders.handleteam_note3 <=> new.handleteam_note3),
        new.dw_updatedat,
        handle_deliveryorders.dw_updatedat
    ),
    handle_deliveryorders.scan_deliveryorder_at = coalesce(new.scan_deliveryorder_at, handle_deliveryorders.scan_deliveryorder_at),
    handle_deliveryorders.handleteam_note1 = coalesce(new.handleteam_note1, handle_deliveryorders.handleteam_note1),
    handle_deliveryorders.handleteam_note2 = coalesce(new.handleteam_note2, handle_deliveryorders.handleteam_note2),
    handle_deliveryorders.handleteam_note3 = coalesce(new.handleteam_note3, handle_deliveryorders.handleteam_note3);

--name: shopeeorders
insert into shopeeorders
values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
as new
on duplicate key update
    shopeeorders.packageid = new.packageid,
    shopeeorders.courier = new.courier,
    shopeeorders.createdat = new.createdat,
    shopeeorders.pickupat = new.pickupat,
    shopeeorders.completedat = new.completedat,
    shopeeorders.orderstatus = new.orderstatus,
    shopeeorders.cancel_reason = new.cancel_reason,
    shopeeorders.buyer_accountname = new.buyer_accountname,
    shopeeorders.returned_orderids = new.returned_orderids,
    shopeeorders.buyer_paymentmethod = new.buyer_paymentmethod,
    shopeeorders.collectedvalue_theory = new.collectedvalue_theory,
    shopeeorders.buyerpaidvalue = new.buyerpaidvalue,
    shopeeorders.shippingcost = new.shippingcost,
    shopeeorders.shippingcostdiscounted_byplatform = new.shippingcostdiscounted_byplatform,
    shopeeorders.shippingcostdiscounted_byseller = new.shippingcostdiscounted_byseller,
    shopeeorders.delivery_orderid = new.delivery_orderid,
    shopeeorders.shopname = new.shopname,
    shopeeorders.dw_updatedat = new.dw_updatedat;

--name: shopeeorderdetails
insert into shopeeorderdetails
values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
as new
on duplicate key update
    shopeeorderdetails.productid = new.productid,
    shopeeorderdetails.productname = new.productname,
    shopeeorderdetails.product_skuname = new.product_skuname,
    shopeeorderdetails.quantity = new.quantity,
    shopeeorderdetails.displayprice = new.displayprice,
    shopeeorderdetails.realprice = new.realprice,
    shopeeorderdetails.shopdiscount_allquantities = new.shopdiscount_allquantities,
    shopeeorderdetails.shopeediscount_allquantities = new.shopeediscount_allquantities,
    shopeeorderdetails.dw_updatedat = new.dw_updatedat;

--name: tiktokorders
insert into tiktokorders
values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
as new
on duplicate key update
    tiktokorders.create_time = new.create_time,
    tiktokorders.collection_time = new.collection_time,
    tiktokorders.delivery_time = new.delivery_time,
    tiktokorders.cancel_time = new.cancel_time,
    tiktokorders.status = new.status,
    tiktokorders.cancel_reason = new.cancel_reason,
    tiktokorders.buyer_email = new.buyer_email,
    tiktokorders.payment_method_name = new.payment_method_name,
    tiktokorders.original_shipping_fee = new.original_shipping_fee,
    tiktokorders.actual_shipping_fee = new.actual_shipping_fee,
    tiktokorders.shipping_fee_platform_discount = new.shipping_fee_platform_discount,
    tiktokorders.shipping_fee_seller_discount = new.shipping_fee_seller_discount,
    tiktokorders.tracking_number = new.tracking_number,
    tiktokorders.shipping_provider = new.shipping_provider,
    tiktokorders.buyeraddress_lv0 = new.buyeraddress_lv0,
    tiktokorders.buyeraddress_lv1 = new.buyeraddress_lv1,
    tiktokorders.buyeraddress_lv2 = new.buyeraddress_lv2,
    tiktokorders.return_reason = new.return_reason,
    tiktokorders.returned_trackingnumber = new.returned_trackingnumber,
    tiktokorders.returnstatus = new.returnstatus,
    tiktokorders.returnshippingfee_paidbybuyer = new.returnshippingfee_paidbybuyer,
    tiktokorders.returnshippingfee_paidbyplatform = new.returnshippingfee_paidbyplatform,
    tiktokorders.returnshippingfee_paidbyseller = new.returnshippingfee_paidbyseller,
    tiktokorders.shopname = new.shopname,
    tiktokorders.dw_updatedat = new.dw_updatedat;

--name: tiktokorderdetails
insert into tiktokorderdetails
values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
as new
on duplicate key update
    tiktokorderdetails.productid = new.productid,
    tiktokorderdetails.productname = new.productname,
    tiktokorderdetails.product_skuname = new.product_skuname,
    tiktokorderdetails.displayprice = new.displayprice,
    tiktokorderdetails.quantity = new.quantity,
    tiktokorderdetails.shopdiscount_allquantities = new.shopdiscount_allquantities,
    tiktokorderdetails.tiktokdiscount_allquantities = new.tiktokdiscount_allquantities,
    tiktokorderdetails.dw_updatedat = new.dw_updatedat;

--name: tiktok_reconciliation
insert into tiktok_reconciliation
values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
as new
on duplicate key update
    tiktok_reconciliation.dw_updatedat = IF(
        NOT (tiktok_reconciliation.transactiontype <=> new.transactiontype)
        OR NOT (tiktok_reconciliation.transactiontime <=> new.transactiontime)
        OR NOT (tiktok_reconciliation.settlement_amount <=> new.settlement_amount)
        OR NOT (tiktok_reconciliation.revenue <=> new.revenue)
        OR NOT (tiktok_reconciliation.subtotal_after_discount <=> new.subtotal_after_discount)
        OR NOT (tiktok_reconciliation.subtotal_before_discount <=> new.subtotal_before_discount)
        OR NOT (tiktok_reconciliation.seller_discount <=> new.seller_discount)
        OR NOT (tiktok_reconciliation.refund_subtotal_after_discount <=> new.refund_subtotal_after_discount)
        OR NOT (tiktok_reconciliation.refund_subtotal_before_discount <=> new.refund_subtotal_before_discount)
        OR NOT (tiktok_reconciliation.refundforseller_amount <=> new.refundforseller_amount)
        OR NOT (tiktok_reconciliation.totalfee <=> new.totalfee),
        new.dw_updatedat,
        tiktok_reconciliation.dw_updatedat
    ),
    tiktok_reconciliation.transactiontype = new.transactiontype,
    tiktok_reconciliation.transactiontime = new.transactiontime,
    tiktok_reconciliation.settlement_amount = new.settlement_amount,
    tiktok_reconciliation.revenue = new.revenue,
    tiktok_reconciliation.subtotal_after_discount = new.subtotal_after_discount,
    tiktok_reconciliation.subtotal_before_discount = new.subtotal_before_discount,
    tiktok_reconciliation.seller_discount = new.seller_discount,
    tiktok_reconciliation.refund_subtotal_after_discount = new.refund_subtotal_after_discount,
    tiktok_reconciliation.refund_subtotal_before_discount = new.refund_subtotal_before_discount,
    tiktok_reconciliation.refundforseller_amount = new.refundforseller_amount,
    tiktok_reconciliation.totalfee = new.totalfee;

--name: dim_product
insert into dim_product
values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
as new
on duplicate key update
    dim_product.retailprice = new.retailprice,
    dim_product.cate_purpose = new.cate_purpose,
    dim_product.cate_color = new.cate_color,
    dim_product.cate_fabric = new.cate_fabric,
    dim_product.cate_collar = new.cate_collar,
    dim_product.cate_sleeve = new.cate_sleeve,
    dim_product.cate_sleevelong = new.cate_sleevelong,
    dim_product.cate_dresstype = new.cate_dresstype,
    dim_product.cate_fabricpattern = new.cate_fabricpattern;