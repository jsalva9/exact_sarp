from abc import ABC
import gurobipy as gp

from utils import Formulation, Instance, Solution


class MTZFormulation(Formulation):
    def __init__(self, inst: Instance, activations: dict = None):
        super().__init__(inst, activations)
        self.x = {}
        self.y = {}
        self.u = {}
        self.z = None

    def define_variables(self):
        for i in self.instance.N_0:
            for k in self.instance.K:
                self.y[i, k] = self.solver.addVar(vtype=gp.GRB.BINARY, name=f'y_{i}_{k}', lb=0, ub=1)
        for i in self.instance.N_0:
            for j in self.instance.N_0:
                for k in self.instance.K:
                    self.x[i, j, k] = self.solver.addVar(vtype=gp.GRB.BINARY, name=f'x_{i}_{j}_{k}', lb=0, ub=1)
        for i in self.instance.N:
            self.u[i] = self.solver.addVar(vtype=gp.GRB.INTEGER, name=f'u_{i}', lb=0,
                                           ub=len(self.instance.N) - 1)
        self.z = self.solver.addVar(vtype=gp.GRB.CONTINUOUS, name='z', lb=0, ub=gp.GRB.INFINITY)

    def constraint_define_obj(self):
        for c in self.instance.C:
            self.solver.addConstr(
                self.z * self.instance.tau[c] <= gp.quicksum(self.instance.alpha[i, c] * self.y[i, k]
                                                             for i in self.instance.N for k in self.instance.K),
                name=f'define_obj_{c}'
            )

    def constraint_leave(self):
        for i in self.instance.N_0:
            for k in self.instance.K:
                self.solver.addConstr(
                    gp.quicksum(self.x[i, j, k] for j in self.instance.N_0) == self.y[i, k],
                    name=f'leave_{i}_{k}'
                )

    def constraint_enter(self):
        for i in self.instance.N_0:
            for k in self.instance.K:
                self.solver.addConstr(
                    gp.quicksum(self.x[j, i, k] for j in self.instance.N_0) == self.y[i, k],
                    name=f'enter_{i}_{k}'
                )

    def constraint_visit(self):
        for i in self.instance.N:
            self.solver.addConstr(
                gp.quicksum(self.y[i, k] for k in self.instance.K) <= 1,
                name=f'visit_{i}'
            )

    def constraint_leave_depot(self):
        self.solver.addConstr(
            gp.quicksum(self.y[0, k] for k in self.instance.K) == len(self.instance.K),
            name='leave_depot'
        )

    def constraint_max_time(self):
        for k in self.instance.K:
            self.solver.addConstr(
                gp.quicksum(self.instance.t[i, j] * self.x[i, j, k]
                            for i in self.instance.N_0 for j in self.instance.N_0) <= self.instance.T_max,
                name=f'max_time_{k}'
            )

    def constraint_mtz(self):
        for i in self.instance.N:
            for j in self.instance.N:
                if i == j:
                    continue
                for k in self.instance.K:
                    self.solver.addConstr(
                        self.u[i] - self.u[j] + len(self.instance.N) * (self.x[i, j, k]) <= len(self.instance.N) - 1,
                        name=f'mtz_{i}_{j}_{k}'
                    )

    def constraint_not_stay(self):
        for i in self.instance.N_0:
            for k in self.instance.K:
                self.solver.addConstr(
                    self.x[i, i, k] == 0,
                    name=f'not_stay_{i}_{k}'
                )

    def fill_constraints(self):
        # Get constraint names by looking at attributes (methods) with prefix 'constraint_'
        constraint_names = [method_name[11:] for method_name in dir(self) if method_name.startswith('constraint_')]

        for constraint_name in constraint_names:
            self.constraints[constraint_name] = getattr(self, f'constraint_{constraint_name}')

    def define_objective(self):
        self.solver.setObjective(self.z, gp.GRB.MAXIMIZE)

    def build_solution(self) -> Solution:
        x = {
            (i, j, k): 1 if self.x[i, j, k].X > 0.5 else 0
            for i in self.instance.N_0
            for j in self.instance.N_0
            for k in self.instance.K
        }
        return Solution(self.instance, x, self.solver.objVal)