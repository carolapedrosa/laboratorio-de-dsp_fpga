VECTOR_SIZE equ 3 ;Vectores de tres dimensiones para que el loop sea corto pero se vea su efecto.
	
	ORG X:$0000
VECTOR_A equ * ;De la misma forma que lo hacíamos con el HC11, asignamos a VECTOR_A la ubicación en memoria donde empiezan los elementos del vector A.
	dc -0.25
	dc -0.5
	dc 0.875

VECTOR_B equ *
	dc 0.15
	dc 0.75
	dc 0.5
	
	ORG p:$e000
main
	
	;El programa recibe la dirección de inicio de los vectores en r0 y r4.
	move #VECTOR_A,r0
	move #VECTOR_B,r4
	move #VECTOR_SIZE,n0
	;Ahora debo hacer un loop el cual compare los modulos de los elementos y guarde el más grande en B.
	.LOOP n0 ;Así es el loop, el cual repetirá su contenido n0 veces sin contemplar condición alguna.
		move x:(r0)+,a ;Cargo en a el contenido en la primer posicion de memoria donde se ubica el vector, luego posincremento el registro con dicha posición.
		move x:(r4),b ;Hago lo mismo con el vector B, en el acumulador b. No hago posincremento porque viene luego.
		cmpm b,a ;Compara pero no guarda el resultado. Sólo actualiza el status register.
		;Esto es |D| - |S| para sintaxis CMPM S,D. Entonces, si S es mayor a D (en módulo) es negativo. 
		;Entonces N nos dice si A o B es mayor. Si A es mayor, N y V valen 0.
		tge a,b ;a es el source, b es el destination. Como el elemento más grande en módulo debe guardarse en B, solo tiene sentido que el source sea a, sino queda como está.
		move b,x:(r4)+ ;Guardo el valor de acc b en el VECTOR_B. Ahora hago el posincremento.
	.ENDL
	end main