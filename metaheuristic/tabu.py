"""Tabu search metaheuristic implementation."""

import copy
import pprint
import random
from enum import Enum
from typing import Optional
from wsry import WSRY
from common import (
    check_overlap,
    nucleotide_to_weak_strong,
    nucleotide_to_purine_pyrimidine,
)
from reconstruction_data import ReconstructionData


class Moves(Enum):
    """All possible moves in tabu search."""

    INSERT_OLIGO = 1
    DELETE_OLIGO = 2
    DELETE_CLUSTER = 3
    SHIFT_OLIGO = 4
    SHIFT_CLUSTER = 5


class Tabu:
    """Class for tabu search metaheuristic."""

    @staticmethod
    def is_in_cluster(ws: WSRY, idx: int) -> bool:  # VERIFY!
        """Check if oligo at idx is in cluster."""
        biggest_possible_overlap = len(ws.start_converted) - 1

        if (
            idx != len(ws.path) - 1
            and ws.depth[idx - 1] == biggest_possible_overlap
            and ws.depth[idx] == biggest_possible_overlap
        ):
            return True
        return False

    def __init__(self, tabu_size, number_of_iterations, number_of_neighbours):
        self.tabu_size = tabu_size
        self.tabu_list_ws = []
        self.tabu_list_ry = []
        self.number_of_iterations = number_of_iterations
        self.number_of_neighbours = number_of_neighbours

    def add(self, move_ws, move_ry):
        """Add move to tabu list and remove oldest move if list is full."""
        self.tabu_list_ws.append(move_ws)
        self.tabu_list_ry.append(move_ry)
        if len(self.tabu_list_ws) > self.tabu_size:
            self.tabu_list_ws.pop(0)
            self.tabu_list_ry.pop(0)

    def is_tabu(self, move):  # VERIFY!
        """Check if move is in tabu list."""
        return (move in self.tabu_list_ws) or (move in self.tabu_list_ry)

    def choose_position_outside_cluster(self, ws: WSRY) -> Optional[int]:
        """Choose random position (not index) outside cluster. <1, len(ws.depth)>. Last position of path is never a cluster."""
        while True:
            pos = random.randint(1, len(ws.path))  # randint or incrementing index?
            if Tabu.is_in_cluster(ws, pos):
                continue
            break
        return pos

    def generate_neighbour_insert_oligo(
        self,
        ws: WSRY,
        ry: WSRY,
        not_used_not_tabu_oligos_ws,
        not_used_not_tabu_oligos_ry,
    ) -> tuple[WSRY, WSRY] | tuple[()]:
        """Generate neighbours for current solution by inserting oligo."""

        # ws i ry muszą mieć ten sam ostatni nukleotyd oraz mieć identyczny overlap z oligo przed miejscem wstawienia

        # find index where to insert (take care of clusters). skip 0 index
        idx_to_insert = self.choose_position_outside_cluster(ws)

        if idx_to_insert is not None:
            previous_oligo_ws = ws.path[idx_to_insert - 1]
            previous_oligo_ry = ry.path[idx_to_insert - 1]

            random.shuffle(not_used_not_tabu_oligos_ws)
            for tmp_oligo_ws in not_used_not_tabu_oligos_ws:
                for tmp_oligo_ry in not_used_not_tabu_oligos_ry:
                    if tmp_oligo_ws[-1] == tmp_oligo_ry[-1]:
                        oligo_ws_overlap = check_overlap(
                            previous_oligo_ws[:-1]
                            + nucleotide_to_weak_strong[
                                previous_oligo_ws[-1]
                            ],  # temporary convert last nucleotide
                            tmp_oligo_ws,
                            len(tmp_oligo_ws),
                        )
                        oligo_ry_overlap = check_overlap(
                            previous_oligo_ry[:-1]
                            + nucleotide_to_purine_pyrimidine[previous_oligo_ry[-1]],
                            tmp_oligo_ry,
                            len(tmp_oligo_ry),
                        )
                        # print(oligo_ws_overlap, oligo_ry_overlap, idx_to_insert)
                        if (
                            oligo_ws_overlap != 0
                            and oligo_ws_overlap == oligo_ry_overlap
                        ):
                            new_ws = copy.deepcopy(ws)
                            new_ry = copy.deepcopy(ry)
                            new_ws.path.insert(idx_to_insert, tmp_oligo_ws)
                            new_ry.path.insert(idx_to_insert, tmp_oligo_ry)
                            new_ws.depth.insert(idx_to_insert, oligo_ws_overlap)
                            new_ry.depth.insert(idx_to_insert, oligo_ry_overlap)
                            return (new_ws, new_ry)

        return ()

    def generate_neighbour_delete_oligo(
        self,
        ws: WSRY,
        ry: WSRY,
        not_used_not_tabu_oligos_ws,
        not_used_not_tabu_oligos_ry,
    ) -> tuple[WSRY, WSRY] | tuple[()]:  # VERIFY!
        """Generate neighbours for current solution by deleting oligo."""
        random_delete_idx = self.choose_position_outside_cluster(ws)
        if random_delete_idx is not None:
            random_delete_idx = (
                random_delete_idx
                if random_delete_idx != len(ws.path)
                else len(ws.path) - 1
            )
            if not self.is_tabu(ws.path[random_delete_idx]):

                ws = copy.deepcopy(ws)
                ry = copy.deepcopy(ry)
                ws.path.pop(random_delete_idx)
                ry.path.pop(random_delete_idx)
                ws.depth.pop(random_delete_idx)
                ry.depth.pop(random_delete_idx)

                return (ws, ry)
        return ()

    def generate_neighbours(self, ws: WSRY, ry: WSRY) -> tuple[tuple[WSRY, WSRY], ...]:
        """Generate neighbours for current solution."""
        neighbours: list[tuple[WSRY, WSRY]] = []
        ws_paths_set = {str(ws.path)}  # terrible solution, but it works
        not_used_not_tabu_oligos_ws = [
            oligo for oligo in ws.not_used_oligos() if not self.is_tabu(oligo)
        ]
        not_used_not_tabu_oligos_ry = [
            oligo for oligo in ry.not_used_oligos() if not self.is_tabu(oligo)
        ]

        for _ in range(self.number_of_neighbours):
            # chosen_move = random.choice(list(Moves))
            # chosen_move = Moves.INSERT_OLIGO
            chosen_move = Moves.DELETE_OLIGO
            match chosen_move:
                case Moves.INSERT_OLIGO:
                    neighbour = self.generate_neighbour_insert_oligo(
                        ws, ry, not_used_not_tabu_oligos_ws, not_used_not_tabu_oligos_ry
                    )
                case Moves.DELETE_OLIGO:
                    neighbour = self.generate_neighbour_delete_oligo(
                        ws, ry, not_used_not_tabu_oligos_ws, not_used_not_tabu_oligos_ry
                    )
                case Moves.DELETE_CLUSTER:
                    pass
                case Moves.SHIFT_OLIGO:
                    pass
                case Moves.SHIFT_CLUSTER:
                    pass

            if neighbour and str(neighbour[0].path) not in ws_paths_set:
                ws_paths_set.add(str(neighbour[0].path))
                neighbours.append(neighbour)

        return tuple(neighbours)

    def find_solution(
        self,
        ws: WSRY,
        ry: WSRY,
        r: ReconstructionData,
        greedy_solution: tuple[WSRY, WSRY],
    ):
        """
        Find solution using tabu search.
        ws, ry - WSRY objects with initial paths
        """
        best_solution = greedy_solution
        neighbours = self.generate_neighbours(best_solution[0], best_solution[1])
        print(best_solution)
        for neighbour in neighbours:
            print(neighbour[0], neighbour[1])

        # for i in range(self.number_of_iterations):
        #     pass
