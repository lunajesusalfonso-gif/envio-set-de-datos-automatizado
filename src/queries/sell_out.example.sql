-- Consulta de ejemplo. Copia este archivo como sell_out.sql y escribe tu consulta real.
-- sell_out.sql esta en .gitignore: la consulta productiva no se versiona.
SELECT
    "CLIENTE"        AS "# de cliente",
    "TIENDA"         AS "Nombre de tienda",
    "FECHA"          AS "Fecha de transaccion de venta",
    "FACTURA"        AS "Numero de factura",
    "SKU"            AS "SKU",
    SUM("PIEZAS")    AS "Numero de piezas vendidas",
    ROUND(SUM("MONTO"), 2) AS "Monto de venta"
FROM "<ESQUEMA>"."<VISTA_DE_VENTAS>"
WHERE "FECHA" BETWEEN TO_DATE('<FECHA_INICIO>') AND TO_DATE('<FECHA_FIN>')
GROUP BY "CLIENTE", "TIENDA", "FECHA", "FACTURA", "SKU";
