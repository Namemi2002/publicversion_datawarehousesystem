delete from nhanhvnorderdetails
where orderid in (
    select orderid from nhanhvnorders
    where (orderstatus = 'don moi' or orderstatus = 'cho khach xac nhan') and created_at >= '{startdate}' and created_at <= '{enddate}'
);
delete from nhanhvnorders
where (orderstatus = 'don moi' or orderstatus = 'cho khach xac nhan') and created_at >= '{startdate}' and created_at <= '{enddate}';