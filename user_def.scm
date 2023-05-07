(define (caar x) (car (car x)))
(define (cadr x) (car (cdr x)))
(define (cdar x) (cdr (car x)))
(define (cddr x) (cdr (cdr x)))


; Some utility functions that you may find useful to implement


(define (zip pairs)
  (list (map car pairs) (map cadr pairs))
)


;; Returns a list of two-element lists
(define (enumerate s)
  (define (enum-iter n s)
      (if (null? s) 
        nil
        (cons
            (list n (car s))
            (enum-iter (+ n 1) (cdr s))
        )
      )
  )
  (enum-iter 0 s)
)


;; Merge two lists LIST1 and LIST2 according to COMP and return
;; the merged lists.
(define (merge comp list1 list2)
      (cond 
      ((null? list1) list2)
      ((null? list2) list1)
      (else 
      (if 
        (comp (car list1) (car list2))
        (cons (car list1) (merge comp (cdr list1) list2))
        (cons (car list2)  (merge comp (cdr list2) list1))
        ))))


;; Returns a function that checks if an expression is the special form FORM
(define (check-special form)
  (lambda (expr) (equal? form (car expr))))

(define lambda? (check-special 'lambda))
(define define? (check-special 'define))
(define quoted? (check-special 'quote))
(define let?    (check-special 'let))


;; Converts all let special forms in EXPR into equivalent forms using lambda
(define (let-to-lambda expr)
(cond ((atom? expr)
       expr 
       )
      ((quoted? expr)
       expr
       )
      ((or (lambda? expr)
           (define? expr))
       (let ((form   (car expr))
             (params (cadr expr))
             (body   (cddr expr)))
         (cons form (cons (map let-to-lambda params) (map let-to-lambda body)))
         ))
      ((let? expr)
       (let ((values (cadr expr))
             (body   (cddr expr)))
         (cons (cons 'lambda (cons (car (zip (let-to-lambda values))) (let-to-lambda body))) (cadr (zip (let-to-lambda values))))
         ))
      (else
       (map let-to-lambda expr)
       )))

