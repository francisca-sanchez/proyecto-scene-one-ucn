# 6. Plan de pruebas

Pruebas **manuales** de aceptación, pensadas para ejecutarse sobre una base con los datos de `database/datos_demo.sql`.
La columna *Resultado* se completa al ejecutar cada prueba (✔ pasó · ✘ falló) junto con la fecha y quién la hizo.

## 6.1 Tienda

| ID | Prueba | Pasos | Resultado esperado | Resultado |
|---|---|---|---|---|
| PT-01 | Catálogo agrupado | Abrir la tienda con "Polera Nightfall" en tallas S, M y L | Una sola tarjeta con selector de talla (S, M, L); el precio cambia con la talla | ✔ |
| PT-02 | Stock oculto | Revisar una tarjeta | No se muestra la cantidad de stock | ✔ |
| PT-03 | Cantidad máxima | Elegir una cantidad igual al stock y agregar; intentar agregar más | No permite superar el stock; aparece el aviso | ✔ |
| PT-04 | Actualización automática | Con la tienda abierta, agregar un producto desde Inventario | Aparece en la tienda en unos 15 segundos sin recargar | ✔ |
| PT-05 | Carrito | Agregar 2 prendas y abrir *Mi reserva* | Se ve foto, talla, precio y cantidad; el total coincide con la suma | ✔ |
| PT-06 | Cambiar cantidad y quitar | Cambiar una cantidad y quitar la otra prenda | El total se actualiza correctamente | ✔ |
| PT-07 | Código válido | Aplicar `BIENVENIDA10` | Se muestra el descuento y el total baja un 10 % | ✔ |
| PT-08 | Código inválido | Aplicar un código inexistente, uno vencido y uno agotado | Mensaje claro en cada caso; el total no cambia | ✔ |
| PT-09 | Reserva sin correo | Confirmar la reserva sin correo | Aviso de que falta un correo válido; no se crea la reserva | ✔ |
| PT-10 | Reserva correcta | Completar nombre y correo y confirmar | Mensaje de confirmación, boleta en pantalla y correo recibido | ✔ |
| PT-11 | Stock apartado | Reservar 2 unidades y revisar el inventario | El stock bajó en 2 | ✔ |

## 6.2 Reservas y punto de venta

| ID | Prueba | Pasos | Resultado esperado | Resultado |
|---|---|---|---|---|
| PT-12 | Pago en efectivo de una reserva | En Reservas, registrar pago en efectivo por el total y confirmar la venta | Reserva *vendida*, comprobante generado, cliente creado | ✔ |
| PT-13 | Transferencia exige captura | Registrar pago por transferencia sin subir imagen | No permite guardar y pide la captura | ✔ |
| PT-14 | Campo de captura condicional | Alternar entre Efectivo y Transferencia en *Registrar pago* | El campo de captura aparece solo con Transferencia | ✔ |
| PT-15 | Cancelar reserva | Cancelar una reserva con código de descuento | El stock vuelve al inventario y el cupo del código se libera | ✔ |
| PT-16 | Venta con varias prendas | En el punto de venta agregar 2 prendas distintas y 1 repetida | La venta suma correctamente y el stock baja en cada una | ✔ |
| PT-17 | Venta sin stock | Intentar vender más unidades que las disponibles | No lo permite | ✔ |
| PT-18 | Venta en efectivo | Registrar venta con nombre y pago en efectivo | Aparece el comprobante con el total y los datos del cliente | ✔ |
| PT-19 | Venta por transferencia | Registrar venta por transferencia con captura | El comprobante incluye la captura | ✔ |

## 6.3 Inventario, clientes y descuentos

| ID | Prueba | Pasos | Resultado esperado | Resultado |
|---|---|---|---|---|
| PT-20 | Agregar otra talla | Agregar producto eligiendo una prenda existente y una talla nueva | Se copian categoría, precio y foto; en la tienda aparece la talla nueva | ✔ |
| PT-21 | Talla repetida | Agregar una talla que ya existe | El stock se suma a la fila existente | ✔ |
| PT-22 | Renombrar categoría | Renombrar una categoría en uso | Todos los productos muestran el nuevo nombre | ✔ |
| PT-23 | Cliente repetido | Hacer dos ventas al mismo Instagram | Un solo cliente con 2 compras y el total acumulado | ✔ |
| PT-24 | Ranking de clientes | Ordenar por *Mayor total gastado* | El cliente que más gastó aparece primero | ✔ |
| PT-25 | Crear código con cupos | Crear un código con 1 cupo y usarlo dos veces | La segunda vez se rechaza por falta de cupos | ✔ |

## 6.4 Finanzas

| ID | Prueba | Pasos | Resultado esperado | Resultado |
|---|---|---|---|---|
| PT-26 | Totales coherentes | Hacer una venta con descuento y revisar Finanzas | El total recaudado coincide con lo cobrado | ✔ |
| PT-27 | Corregir total | Corregir el total de una venta indicando un motivo | Cambian Finanzas, la ficha del cliente y el comprobante; queda el registro | ✔ |
| PT-28 | Corrección sin motivo | Intentar corregir sin escribir el motivo | No lo permite | ✔ |
| PT-29 | Cerrar tanda | Cerrar la tanda con un nombre | Finanzas queda en cero y aparece la fila en el historial con las fechas | ✔ |
| PT-30 | Venta tras el cierre | Hacer una venta nueva después de cerrar | Aparece solo en la tanda nueva | ✔ |
| PT-31 | Deshacer cierre | Deshacer el último cierre | Las ventas vuelven a contarse en la tanda actual | ✔ |
| PT-32 | Tanda cerrada protegida | Intentar corregir una venta de una tanda cerrada | Lo bloquea con un mensaje claro | ✔ |

## 6.5 Diseño y acceso

| ID | Prueba | Pasos | Resultado esperado | Resultado |
|---|---|---|---|---|
| PT-33 | Login incorrecto | Entrar con una contraseña errónea | Mensaje de error; no se accede al panel | ✔ |
| PT-34 | Cambio parcial de diseño | Cambiar solo un color y guardar | Se aplica ese color; el resto del diseño no cambia | ✔ |
| PT-35 | Tipografía | Elegir otra de las 5 tipografías | La letra cambia en toda la aplicación | ✔ |


