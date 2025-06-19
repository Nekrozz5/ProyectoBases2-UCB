from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clave_supersecreta'

# Conexion MongoDB
cliente = MongoClient("mongodb://localhost:27017")
db = cliente["Instrumentos"]
coleccion = db["instrumentos"]
ventas = db["ventas"]
tablatemp = db["tablatemp"]

@app.route('/')
def index():
    categorias = coleccion.distinct("categoria")
    return render_template("index.html", categorias=categorias)

@app.route('/categoria/<categoria>')
def mostrar_categoria(categoria):
    productos = list(coleccion.find({"categoria": categoria}))
    return render_template("categoria.html", categoria=categoria, productos=productos)

@app.route('/producto/<id_producto>')
def detalle_producto(id_producto):
    producto = coleccion.find_one({"id_producto": id_producto})
    if producto:
        coleccion.update_one({"id_producto": id_producto}, {"$inc": {"vistas": 1}})
    return render_template("detalle.html", producto=producto)

@app.route('/agregar/<id_producto>', methods=['POST'])
def agregar_carrito(id_producto):
    producto = coleccion.find_one({"id_producto": id_producto})
    if producto and producto.get("stock", 0) > 0:
        existente = tablatemp.find_one({"id_usuario": "anonimo1", "id_producto": id_producto})
        if existente:
            tablatemp.update_one(
                {"_id": existente["_id"]},
                {"$inc": {"cantidad": 1}}
            )
        else:
            tablatemp.insert_one({
                "id_usuario": "anonimo1",
                "id_producto": producto["id_producto"],
                "nombre": producto["nombre"],
                "precio": producto["precio"],
                "cantidad": 1
            })
    return redirect(url_for('mostrar_categoria', categoria=producto["categoria"]))
@app.route('/eliminar/<id_producto>', methods=['POST'])
def eliminar_producto(id_producto):
    tablatemp.delete_one({
        "id_usuario": "anonimo1",
        "id_producto": id_producto
    })
    return redirect(url_for('ver_carrito'))
@app.route('/actualizar/<id_producto>', methods=['POST'])
def actualizar_cantidad(id_producto):
    nueva_cantidad = int(request.form['cantidad'])
    if nueva_cantidad > 0:
        tablatemp.update_one(
            {"id_usuario": "anonimo1", "id_producto": id_producto},
            {"$set": {"cantidad": nueva_cantidad}}
        )
    return redirect(url_for('ver_carrito'))


@app.route('/carrito')
def ver_carrito():
    carrito = list(tablatemp.find({"id_usuario": "anonimo1"}))
    total = sum(item['precio'] * item['cantidad'] for item in carrito)
    return render_template("carrito.html", productos=carrito, total=total)

@app.route('/pagar', methods=['POST'])
def pagar():
    nombre = request.form['nombre']
    nit = request.form['nit']
    metodo = request.form['metodo']

    carrito = list(tablatemp.find({"id_usuario": "anonimo1"}))
    total = 0
    productos = []

    for item in carrito:
        producto = coleccion.find_one({"id_producto": item["id_producto"]})
        if not producto or producto.get("stock", 0) < item["cantidad"]:
            return render_template("fallo.html", mensaje="Producto sin stock suficiente")

        productos.append({
            "id_producto": item["id_producto"],
            "cantidad": item["cantidad"],
            "precioUnitario": item["precio"]
        })
        total += item["precio"] * item["cantidad"]

    estado_pago = "aprobado" if random.random() <= 0.8 else "rechazado"

    venta = {
        "idFactura": f"FAC-{random.randint(1000,9999)}",
        "nombreComprador": nombre,
        "nit": nit,
        "productos": productos,
        "costoTotal": total,
        "fecha": datetime.now(),
        "metodoPago": metodo,
        "estadoPago": estado_pago
    }

    if estado_pago == "aprobado":
        for item in carrito:
            coleccion.update_one(
                {"id_producto": item["id_producto"]},
                {"$inc": {"stock": -item["cantidad"]}}
            )
        ventas.insert_one(venta)
        tablatemp.delete_many({"id_usuario": "anonimo1"})
        return render_template("exito.html", venta=venta)
    else:
        return render_template("fallo.html", mensaje="El pago fue rechazado")

if __name__ == '__main__':
    app.run(debug=True)
