	ORG X:$0000
	dc $10fedc
	dc $210fed
	dc $4210fe
	dc $84210f
	dc $d84210
	dc $fb8421

	ORG p:$e000

main
	move #$0000,r0
	move #$0000,r4
	move #$ffff,m0
	
	move #$ffff,m4
	move #$0800,sr ;Esto es importante pues enciende el bit s1 del status register. S1 1 y S0 0 es Scale Up mode.
	
	move x:(r0)+,a ;Muevo el contenido de X:$r0 a a1.
	rep #6 ;Repito 6 veces la siguiente instruccion, guardando el valor en el loop counter.
	move a,y:(r4)+ x:(r0)+,a ;Muevo el contenido de a a y en la posición $r4, y los de x en $r0 a a. Posincremento ambos.
	jlc OK ;Jump if limit clear (pag 210 manual DSP Audio Course, 113 del pdf)
	bset #0,y:$100 ;Si me marca un 1 en la posicion $100 de y, entonces L del status register vale 1, pues no hubo jump.
OK  bclr #6,sr ;Clear al bit 6 del SR, que corresponde a L. Es decir, en caso de haberse activado el bit de Limit, se apaga.

	end main
	
	
	
	; Este programa tiene como objetivo demostrar el funcionamiento del bit LIMIT.
	; El bit LIMIT se enciende cuando transfiero de un acumulador (a, en este caso) a un input register (Y, en este caso)
	; y la transferencia deja en el input register un valor que supera o iguala a la unidad en módulo (vease ejemplo página 46).
	; Cuando se supera la unidad y el signo es positivo, se manifiesta almacenando un #7FFFFF, que sería un 0.9999999
	; En caso de ser signo negativo, se guarda un 800000.
	; En el ejemplo existen dos casos donde ocurre esto, siendo el tercer y cuarto numeros cargados que devuelven los valores mencionados en el orden respectivo.
	; Como respuesta, se encendió el bit L y no se realizó el Jump, accediendo al fragmento de código que setea un 1 en Y:$100 para indicarlo.
	; Esto ocurre porque al estar en Scale Up mode, el punto fraccional se pone luego del bit 46.
	; Entonces, $4210FE en A1 tiene el bit 46 en 1. Por ende, al pasarlo a Y (tomando los bits 46-23) se interpreta como un número mayor a 1 y la lógica del limit devuelve 7FFFFF.
	; $84210f tiene un problema similar, pero con los negativos. Produce otro limit.
	; Así, se explica lo ocurrido con el programa a partir de los datos iniciales.
	
	