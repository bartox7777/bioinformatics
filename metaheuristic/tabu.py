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
    def reconstruct_dna(ws: WSRY, ry: WSRY) -> str:
        """
        Reconstruct DNA from WS and RY paths.
        """
        reconstructed_dna = ""
        for ws_oligo, ry_oligo, depth in zip(ws.path, ry.path, ws.depth):
            connected = WSRY.connect_ws_ry(ws_oligo, ry_oligo)
            reconstructed_dna += connected[depth - len(ws_oligo) :]
        return reconstructed_dna

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

    def is_tabu(self, move):
        """Check if move is in tabu list."""
        return (move in self.tabu_list_ws) or (move in self.tabu_list_ry)

    def generate_neighbour_insert_oligo(
        self,
        ws: WSRY,
        ry: WSRY,
        not_used_not_tabu_oligos_ws,
        not_used_not_tabu_oligos_ry,
    ) -> tuple[WSRY, WSRY] | tuple[()]:
        """
        Generate neighbours for current solution by inserting oligo.
        WS and RY must have the same last nucleotide and have the same overlap with the oligo before the insertion point.
        """

        ### INDEX OUTSIDE CLUSTER - BEGIN
        possible_idxs = []
        for idx in range(1, len(ws.path) + 1):
            if (
                idx != len(ws.path)
                and ws.depth[idx - 1] == ws.perfect_overlap
                and ws.depth[idx] == ws.perfect_overlap
            ):
                continue
            possible_idxs.append(idx)
        ### INDEX OUTSIDE CLUSTER - END
        if possible_idxs:

            random.shuffle(not_used_not_tabu_oligos_ws)
            for tmp_oligo_ws in not_used_not_tabu_oligos_ws:
                for tmp_oligo_ry in not_used_not_tabu_oligos_ry:
                    if tmp_oligo_ws[-1] == tmp_oligo_ry[-1]:
                        for idx_to_insert in possible_idxs:
                            new_ws = copy.deepcopy(ws)
                            new_ry = copy.deepcopy(ry)
                            new_ws.path.insert(idx_to_insert, tmp_oligo_ws)
                            new_ry.path.insert(idx_to_insert, tmp_oligo_ry)
                            new_ws.update_depth()
                            new_ry.update_depth()

                            # if new_ws.depth != new_ry.depth or 0 in new_ws.depth[1:]:
                            if new_ws.depth != new_ry.depth:
                                continue
                            return (new_ws, new_ry)

        return ()

    def generate_neighbour_delete_oligo(
        self,
        ws: WSRY,
        ry: WSRY,
        skip_tabu_check=False,
    ) -> tuple[WSRY, WSRY] | tuple[()]:
        """Generate neighbours for current solution by deleting oligo."""

        ### INDEX OUTSIDE CLUSTER - BEGIN
        while True:
            random_delete_idx = random.randint(
                1, len(ws.path) - 1
            )  # randint or incrementing index?
            if (
                random_delete_idx != len(ws.path) - 1
                and ws.depth[random_delete_idx] == ws.perfect_overlap
                and ws.depth[random_delete_idx + 1] == ws.perfect_overlap
            ):
                continue
            break
        ### INDEX OUTSIDE CLUSTER - END

        if not self.is_tabu(ws.path[random_delete_idx]) or skip_tabu_check:

            ws = copy.deepcopy(ws)
            ry = copy.deepcopy(ry)
            ws.path.pop(random_delete_idx)
            ry.path.pop(random_delete_idx)
            ws.update_depth()
            ry.update_depth()

            if ws.depth == ry.depth:
                return (ws, ry)
        return ()

    def generate_neighbour_shift_oligo(
        self, ws: WSRY, ry: WSRY
    ) -> tuple[WSRY, WSRY] | tuple[()]:
        """Generate neighbours for current solution by shifting oligo."""
        ### INDEX OUTSIDE CLUSTER - BEGIN - choose random oligo to shift
        while True:
            random_oligo_idx = random.randint(
                1, len(ws.path) - 1
            )  # randint or incrementing index?
            if (
                random_oligo_idx != len(ws.path) - 1
                and ws.depth[random_oligo_idx] == ws.perfect_overlap
                and ws.depth[random_oligo_idx + 1] == ws.perfect_overlap
            ):
                continue
            break
        ### INDEX OUTSIDE CLUSTER - END

        if not self.is_tabu(ws.path[random_oligo_idx]):

            ws = copy.deepcopy(ws)
            ry = copy.deepcopy(ry)
            oligo_ws = ws.path.pop(random_oligo_idx)
            oligo_ry = ry.path.pop(random_oligo_idx)
            ws.update_depth()
            ry.update_depth()

            idxs = []
            ### INDEX OUTSIDE CLUSTER - BEGIN - choose random index to insert
            for idx_to_insert in range(1, len(ws.path) + 1):
                if (
                    idx_to_insert != len(ws.path)
                    and ws.depth[idx_to_insert - 1] == ws.perfect_overlap
                    and ws.depth[idx_to_insert] == ws.perfect_overlap
                ):
                    continue
                idxs.append(idx_to_insert)
            ### INDEX OUTSIDE CLUSTER - END
            random.shuffle(idxs)
            for i in idxs:
                ws.path.insert(i, oligo_ws)
                ry.path.insert(i, oligo_ry)
                ws.update_depth()
                ry.update_depth()
                # if ws.depth == ry.depth and 0 not in ws.depth[1:]: # do we allow 0 in depth?
                if ws.depth == ry.depth:
                    return (ws, ry)
                ws.path.pop(i)
                ry.path.pop(i)
        return ()

    def generate_neigbour_delete_cluster(
        self, ws: WSRY, ry: WSRY
    ) -> tuple[WSRY, WSRY] | tuple[()]:
        """Generate neighbours for current solution by deleting cluster."""
        # find indexes of first elements of clusters
        ws = copy.deepcopy(ws)
        ry = copy.deepcopy(ry)

        begin_of_cluster = False
        cluster_indexes = []
        for i in range(1, len(ws.path) - 1):
            if ws.depth[i] == ws.perfect_overlap:
                if begin_of_cluster is False and ws.depth[i + 1] == ws.perfect_overlap:
                    cluster_indexes.append(i)
                    begin_of_cluster = True
            else:
                begin_of_cluster = False

        if cluster_indexes:
            random_cluster_idx = random.choice(cluster_indexes)
            while (
                random_cluster_idx < len(ws.path)
                and ws.depth[random_cluster_idx] == ws.perfect_overlap
            ):
                ws.path.pop(random_cluster_idx)
                ry.path.pop(random_cluster_idx)
                ws.depth.pop(random_cluster_idx)
                ry.depth.pop(random_cluster_idx)

            ws.update_depth()
            ry.update_depth()
            if ws.depth == ry.depth:
                return (ws, ry)

        return ()

    def generate_neighbour_shift_cluster(
        self, ws: WSRY, ry: WSRY
    ) -> tuple[WSRY, WSRY] | tuple[()]:
        """Generate neighbours for current solution by shifting cluster."""
        ws = copy.deepcopy(ws)
        ry = copy.deepcopy(ry)
        begin_of_cluster = False
        cluster_indexes = []
        for i in range(1, len(ws.path) - 1):
            if ws.depth[i] == ws.perfect_overlap:
                if begin_of_cluster is False and ws.depth[i + 1] == ws.perfect_overlap:
                    cluster_indexes.append(i)
                    begin_of_cluster = True
            else:
                begin_of_cluster = False

        cluster_to_shift_ws = []
        cluster_to_shift_ry = []

        if cluster_indexes:
            random_cluster_idx = random.choice(cluster_indexes)
            while (
                random_cluster_idx < len(ws.path)
                and ws.depth[random_cluster_idx] == ws.perfect_overlap
            ):
                cluster_to_shift_ws.append(ws.path.pop(random_cluster_idx))
                cluster_to_shift_ry.append(ry.path.pop(random_cluster_idx))
                ws.depth.pop(random_cluster_idx)
                ry.depth.pop(random_cluster_idx)

            while True:
                random_idx_to_insert = random.randint(1, len(ws.path))
                if random_idx_to_insert != random_cluster_idx:
                    break
            for i in range(len(cluster_to_shift_ws) - 1, -1, -1):
                ws.path.insert(random_idx_to_insert, cluster_to_shift_ws[i])
                ry.path.insert(random_idx_to_insert, cluster_to_shift_ry[i])

            ws.update_depth()
            ry.update_depth()
            if ws.depth == ry.depth:
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
            # chosen_move = Moves.DELETE_OLIGO
            # chosen_move = Moves.SHIFT_OLIGO
            # chosen_move = Moves.DELETE_CLUSTER
            chosen_move = Moves.SHIFT_CLUSTER
            match chosen_move:
                case Moves.INSERT_OLIGO:
                    neighbour = self.generate_neighbour_insert_oligo(
                        ws, ry, not_used_not_tabu_oligos_ws, not_used_not_tabu_oligos_ry
                    )
                case Moves.DELETE_OLIGO:
                    neighbour = self.generate_neighbour_delete_oligo(ws, ry)
                case Moves.DELETE_CLUSTER:
                    neighbour = self.generate_neigbour_delete_cluster(
                        ws, ry
                    )  # TODO: ws.depth != ry.depth
                case Moves.SHIFT_OLIGO:
                    neighbour = self.generate_neighbour_shift_oligo(
                        ws, ry
                    )  # TODO: seems ok
                case Moves.SHIFT_CLUSTER:
                    neighbour = self.generate_neighbour_shift_cluster(
                        ws, ry
                    )  # TODO: ws.depth != ry.depth

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
        print(best_solution)
        reconstructed_dna = Tabu.reconstruct_dna(best_solution[0], best_solution[1])
        print(reconstructed_dna, len(reconstructed_dna), f"max: {r.length}")
        neighbours = self.generate_neighbours(best_solution[0], best_solution[1])
        for neighbour in neighbours:
            print(neighbour[0], neighbour[1])
            if neighbour[0].depth != neighbour[1].depth:
                print("ERROR - skipped neighbour with different depth")
                continue
            reconstructed_dna = Tabu.reconstruct_dna(neighbour[0], neighbour[1])
            print(reconstructed_dna, len(reconstructed_dna), f"max: {r.length}")
            if len(reconstructed_dna) > r.length:
                print("ERROR - skipped neighbour with too long dna")
                continue
