%% placeholder constantes
step(1..n_step).

% quest(1..2).

% objective(obj_id, quest_id, zones_id)
% objective(1, 1, 1).
% objective(2, 1, 1).
% objective(1, 2, 2).
% objective(2, 2, 1).

zone(-1).

distance(-1,Z,0):- zone(Z). % distance when no zone
distance(Z,-1,0):- zone(Z). % distance when no zone

% distance(Z,Z,0):- zone(Z).
% distance(Z1,Z2,1):- zone(Z1), zone(Z2), Z1!=Z2.

%% Préconditions de quêtes
%precond(2,1). % 2 need 1

%% Generation des actions
{do(obj(I,Q), T) : objective(I,Q, _)}=1 :- step(T).

%% Generation des couts
cout(C,0) :-  objective(I1,Q1, Z1), do(obj(I1,Q1), 1), distance(250,Z1, C).
{cout(C,T): objective(I1,Q1, Z1), objective(I2,Q2, Z2), distance(Z1,Z2, C)}=1 :-
    do(obj(I1,Q1), T), do(obj(I2,Q2), T+1).

total_cout(X) :- X = #sum {C, S : cout(C,S)}.
%% Contraintes

% contrainte de suite des steps
:- do(obj(_,_),T), T!= 1, not do(obj(_,_),T-1).

% contrainte d'unicité
:- do(obj(I,Q),T1), do(obj(I,Q), T2), T1!=T2.

% contrainte sur l'ordre des quêtes
:- precond(Q2,Q1), do(obj(_,Q1), T1), do(obj(_,Q2), T2), not T1<T2.

% contrainte sur l'ordre des objectif
:- do(obj(I1,Q), T1), do(obj(I2,Q), T2), I1<I2, not T1<T2.

% contrainte d'existence
:- objective(I,Q,_), not do(obj(I,Q), _).


#minimize {C: total_cout(C)}.
#show do/2 .
