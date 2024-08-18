#!/usr/bin/env python3

import sys
import os
import operator
import numpy as np

# Plotting libs
import matplotlib
import pylab as plt
from matplotlib import cm

from make_lammps_input import (
    setup_problem,
    make_stack_twin_test,
    make_refine_us,
    make_refine_ut,
    make_gammasurface_moves,
    compute_eq_latconst,
)

# for Crystal Genome
from kim_tools import CrystalGenomeTestDriver

#for timer
import time

matplotlib.use("Agg")  # Use backend for non-interactive plotting

class TestDriver(CrystalGenomeTestDriver):
    """
    Gamma surface calculation for crystal lattice

    Description: This script computes the gamma surface energies of a general crystal. For more details, refer to README.txt

    Inputs: Pressure   --> (optional) Hydrostatic pressure (bars).  If omitted, the pressure is taken to be zero.
                            If the value specified is non-zero, the lattice constant specified for
                            LatConst will be used to construct an initial lattice geometry for an NPT
                            simulation carried out at the specified pressure and temperature of 1e-4
                            Kelvin from which the actual lattice constant at the specified pressure is
                            calculated.

    Outputs: gamma_us,  frac_us         # Unstable stacking fault energy  (max)
            gamma_isf, frac_isf = 1.0  # Intrinsic stacking fault energy (min)
            gamma_ut,  frac_ut         # Unstable twinning fault energy  (max)
            gamma_esf, frac_esf = 2.0  # Entrinsic stacking fault energy (min)
            FracList  = []             # fractional displacements array
            SFEDList  = []             # stacking fault energy densities (eV/A^2)
            GammaSurf = []             # [frac_along_112, frac_along_110, energy (eV/A^2)] in each row

    Supporting modules used:
        make_lammps_input.py  --> Makes LAMMPS input
        dump_edn.py           --> Dumps output in edn format

    External resources used:
        LAMMPS executable with KIM API support
    """
    
    def _calculate(self, 
                   #structure_index: int, confirm w/ ilia this is legacy
                   pressure = 0.0,
                   Num_layers_gamma_surf = 10,
                   **kwargs):

        # verify with ilia:
            # where to have slip plane, dir1 and dir2, offset and pressure hard coded/input.
        
        # note: don't need pressure b/c first iteration will be 0 only
        # if statement to check for FCC
        if self.prototype_label != 'A_cF4_225_a':
            raise RuntimeError('Only accepts single species FCC')
        

        # assign default for FCC
        # slip_plane = "[111]"
        # slip_direction_1 = [1,1,2]
        # slip_direction_2 = [-1,1,0]
        # slip_plane_offset = 0.25

        # get the necessary parameters
        latconst = self.parameter_values_angstrom[0]
        model = self.kim_model_name
        species = self.stoichiometric_species[0]

        # run simulations
        output_dict = self._main(model, species, latconst, Pressure = pressure, Num_layers_gamma_surf = Num_layers_gamma_surf)
        print([f"{i} = {output_dict[i]}" for i in ['gamma_us', 
                                                   'gamma_isf',
                                                   'gamma_ut',
                                                   'gamma_esf',
                                                   'frac_us',
                                                   'frac_ut']])

        ####################################################
        # PROPERTY WRITING
        ####################################################

        # TODO: update these to latest
        
        # gamma-surface
        self._add_property_instance("gamma-surface-relaxed-fcc-crystal-npt-crystal-genome")
        self._add_common_crystal_genome_keys_to_current_property_instance(write_stress=False,write_temp=False) # last two default to False
        self._add_key_to_current_property_instance("cauchy-stress",
                                                   output_dict['CauchyStress'],
                                                   "bar")
        self._add_key_to_current_property_instance("fault-plane-shift-fraction-110",
                                                   output_dict['Gamma_Y_dir2_frac'])
        self._add_key_to_current_property_instance("fault-plane-shift-fraction-112",
                                                   output_dict['Gamma_X_dir1_frac'])
        self._add_key_to_current_property_instance("gamma-surface",
                                                   output_dict['GammaSurf'],
                                                   "ev/angstrom^2")
        # self._add_key_to_current_property_instance("gamma-surface-plot",
        #                                            output_dict['gamma_surface_plot'])


        # unstable-stacking-energy-fcc-crystal
        self._add_property_instance("unstable-stacking-fault-relaxed-energy-fcc-crystal-npt-crystal-genome")
        self._add_common_crystal_genome_keys_to_current_property_instance(write_stress=False,write_temp=False) # last two default to False
        self._add_key_to_current_property_instance("cauchy-stress",
                                                   output_dict['CauchyStress'],
                                                   "bar")
        self._add_key_to_current_property_instance("unstable-stacking-energy",
                                                   output_dict['gamma_us'],
                                                   "eV/angstrom^2")
        self._add_key_to_current_property_instance("unstable-slip-fraction",
                                                   output_dict["frac_us"])


        # intrinsic-stacking-fault-energy-fcc-crystal
        self._add_property_instance("intrinsic-stacking-fault-relaxed-energy-fcc-crystal-npt-crystal-genome")
        self._add_common_crystal_genome_keys_to_current_property_instance(write_stress=False,write_temp=False) # last two default to False
        self._add_key_to_current_property_instance("cauchy-stress",
                                                   output_dict['CauchyStress'],
                                                   "bar")
        self._add_key_to_current_property_instance("intrinsic-stacking-fault-energy",
                                                   output_dict['gamma_isf'],
                                                   "eV/angstrom^2")


        # unstable-twinning-energy-fcc-crystal
        self._add_property_instance("unstable-twinning-fault-relaxed-energy-fcc-crystal-npt-crystal-genome")
        self._add_common_crystal_genome_keys_to_current_property_instance(write_stress=False,write_temp=False) # last two default to False
        self._add_key_to_current_property_instance("cauchy-stress",
                                                   output_dict['CauchyStress'],
                                                   "bar")
        self._add_key_to_current_property_instance("unstable-twinning-energy",
                                                   output_dict['gamma_ut'],
                                                   "eV/angstrom^2")
        self._add_key_to_current_property_instance("unstable-slip-fraction",
                                                   output_dict['frac_ut'])

        
        # extrinsic-stacking-fault-energy-fcc-crystal
        self._add_property_instance("extrinsic-stacking-fault-relaxed-energy-fcc-crystal-npt-crystal-genome")
        self._add_common_crystal_genome_keys_to_current_property_instance(write_stress=False,write_temp=False) # last two default to False
        self._add_key_to_current_property_instance("cauchy-stress",
                                                   output_dict['CauchyStress'],
                                                   "bar")
        self._add_key_to_current_property_instance("extrinsic-stacking-fault-energy",
                                                   output_dict['gamma_esf'],
                                                   "eV/angstrom^2")

        # stacking-energy-curve-fcc-crystal
        self._add_property_instance("stacking-fault-relaxed-energy-curve-fcc-crystal-npt-crystal-genome")
        self._add_common_crystal_genome_keys_to_current_property_instance(write_stress=False,write_temp=False) # last two default to False
        self._add_key_to_current_property_instance("cauchy-stress",
                                                   output_dict['CauchyStress'],
                                                   "bar")
        self._add_key_to_current_property_instance("fault-plane-shift-fraction",
                                                   output_dict['FracList'])
        self._add_key_to_current_property_instance("fault-plane-energy",
                                                   output_dict['SFEDList'],
                                                   "eV/angstrom^2")


    def _main(self, Model, Species, LatConst, Pressure = 0.0, Num_layers_gamma_surf = 10):
        # Program Parameter Variables
        LatConst_Tol = 10e-4

        if Pressure == float(0):
                msg = (
                    "\nInfo: Pressure was either specified as zero in input or not provided. "
                    "Forgoing lattice constant calculation and "
                    "proceeding with lattice constant specified.\n"
                )
                print(msg)


        # -------------------------------------------------------------------------------
        #                        Program internal Constants
        # -------------------------------------------------------------------------------
        N_Layers = 58  # No. of layers of the (11-1) planes in the periodic cell
        N_Twin_Layers = round(N_Layers / 2)
        Rigid_Grp_SIdx = 15
        Rigid_Grp_EIdx = 45

        # gamma surface specific values
        N_Twin_Layers_gamma_surf = round(Num_layers_gamma_surf / 2)
        Rigid_Grp_SIdx_gamma_surf = 4 # was 15
        Rigid_Grp_EIdx_gamma_surf = 7 # was 45
        Gamma_Nx_dir1 = 20 # was 50, change this from 20 to 3 for testing
        Gamma_Ny_dir2 = 20 # was 50, change this from 20 to 3 for testing

        output_dir = "./output"  # Output directory
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        stack_inp_flnm = output_dir + "/stack.in"  # Input file for LAMMPS
        stack_log_flnm = output_dir + "/stack.log"  # Log file for LAMMPS
        stack_data_flnm = output_dir + "/stack.dat"  # temporary file for lammps output
        stack_results_flnm = output_dir + "/results.edn"  # Results file in .edn format for KIM
        LAMMPS_command = "lammps"

        # -------------------------------------------------------------------------------
        #      Target variables to be calculated (see definitions in header)
        # -------------------------------------------------------------------------------
        gamma_us = 0.0
        gamma_isf = 0.0
        gamma_ut = 0.0
        gamma_esf = 0.0

        frac_us = 0.0
        frac_ut = 0.0
        FracList = []
        SFEDList = []
        Gamma_X_dir1_frac = [0 + x * 1.0 / (Gamma_Nx_dir1 - 1) for x in range(Gamma_Nx_dir1)]
        Gamma_Y_dir2_frac = [0 + y * 1.0 / (Gamma_Ny_dir2 - 1) for y in range(Gamma_Ny_dir2)]
        GammaSurf = []

        if not Pressure:
            # ------------------------------------------------------------------------------
            #                            CASE I - ZERO PRESSURE
            # Either no pressure was specified, or a pressure of zero was specified.
            # Proceed by constructing the FCC lattice using the equilibrium lattice
            # constant given and forming the stacking faults, etc.
            # ------------------------------------------------------------------------------
            Pressure = 0.0

        else:
            # ------------------------------------------------------------------------------
            #                         CASE II - NON-ZERO PRESSURE
            # Use the zero-temperature, zero-pressure equilibrium lattice constant
            # specified in the input to construct the initial FCC lattice for an NPT
            # simulation at 1e-4K and the specified pressure.  After 200,000 timesteps, the
            # length of the supercell along the x direction is parsed from the output and
            # divided by the number of conventional FCC cells along that direction to
            # arrive at the equilibrium lattice constant at the specified pressure.  This
            # lattice constant is then used to construct the lattice geometry for the
            # actual stacking fault calculations.
            # ------------------------------------------------------------------------------
            print(
                "Info: A non-zero pressure of %r bar was specified. Computing the corresponding "
                "FCC lattice constant...\n" % Pressure
            )
            with open(stack_inp_flnm, "w") as fstack:
                InpStr = compute_eq_latconst(
                    Species, Model, LatConst, Pressure, stack_data_flnm
                )
                fstack.write(InpStr)

            # Run the LAMMPS script
            os.system(LAMMPS_command + " -in " + stack_inp_flnm + " -log " + stack_log_flnm)

            # Read the LAMMPS output file for the lattice constant
            with open(stack_data_flnm) as fstack:
                linelist = fstack.readlines()
                linebuf = linelist[0].split()
                LatConst = float(linebuf[0])

            # delete the output file
            os.system("rm " + stack_data_flnm)
            os.system("rm " + stack_inp_flnm)
            print(
                "Info: Calculated an FCC lattice constant of %r corresponding to pressure %r\n"
                % (LatConst, Pressure)
            )

        # ------------------------------------------------------------------------------
        #                            COMPUTE GAMMMA SURFACE
        # ------------------------------------------------------------------------------
        print("***********************************************************")
        print("              COMPUTING GAMMA SURFACE                      ")
        print("***********************************************************")
        time_gamma_start = time.perf_counter()
        with open(stack_inp_flnm, "w") as fstack:
            InpStr = setup_problem(
                Species,
                Model,
                Num_layers_gamma_surf,
                LatConst,
                Pressure,
                Rigid_Grp_SIdx_gamma_surf,
                Rigid_Grp_EIdx_gamma_surf,
                N_Twin_Layers_gamma_surf,
            )
            fstack.write(InpStr)
            InpStr = make_gammasurface_moves(stack_data_flnm, Gamma_Nx_dir1, Gamma_Ny_dir2)
            fstack.write(InpStr)

        # Run the LAMMPS script
        os.system(LAMMPS_command + " -in " + stack_inp_flnm + " -log " + stack_log_flnm)

        # Read the LAMMPS output file
        """-----------------------------------------------------------------------------
        File format: stack.dat
        Line 1: Header
        Line 1+1 to 1+NxPoints*NyPoints: [ 112_frac    110_frac    SFED ]
        -----------------------------------------------------------------------------"""
        with open(stack_data_flnm) as fstack:
            linelist = fstack.readlines()
            # Discard the header, index = 0
            # Read the data into arrays
            count = 1
            for yIdx in range(1, Gamma_Ny_dir2 + 1):
                temp_list_at_each_y = []
                for xIdx in range(1, Gamma_Nx_dir1 + 1):
                    linebuf = linelist[count].split()
                    count = count + 1
                    # Discard x any y coordinates
                    temp_list_at_each_y.append(float(linebuf[2]))
                GammaSurf.append(temp_list_at_each_y)

        # delete the output file
        os.system("rm " + stack_data_flnm)
        os.system("rm " + stack_inp_flnm)

        time_gamma_end = time.perf_counter()

        # ------------------------------------------------------------------------------
        #                       COMPUTE STACKING FAULT ENERGIES
        # ------------------------------------------------------------------------------
        with open(stack_inp_flnm, "w") as fstack:
            InpStr = setup_problem(
                Species,
                Model,
                N_Layers,
                LatConst,
                Pressure,
                Rigid_Grp_SIdx,
                Rigid_Grp_EIdx,
                N_Twin_Layers,
            )
            fstack.write(InpStr)
            InpStr = make_stack_twin_test(stack_data_flnm)
            fstack.write(InpStr)

        time_sf_coarse_start = time.perf_counter()
        # Run the LAMMPS script
        os.system(LAMMPS_command + " -in " + stack_inp_flnm + " -log " + stack_log_flnm)

        # Read the LAMMPS output file
        """-----------------------------------------------------------------------------
        File format: stack.dat
        Line 1:             NPoints 1 nincr nincr
        Line 1+1 to 1+1+2*nincr:    [ column1 = frac_disp, column2 = SFED ]
        Line:                gamma_us
        Line:                gamma_isf
        Line:                gamma_ut
        Line:                gamma_esf
        -----------------------------------------------------------------------------"""
        with open(stack_data_flnm) as fstack:
            linelist = fstack.readlines()
            linebuf = linelist[0].split()
            size_0 = int(linebuf[2])
            size_1 = int(linebuf[3])
            size_2 = int(linebuf[4])
            # Read the data into arrays
            listend = 1 + size_0 + size_1 + size_2
            for i in range(1, listend):
                linebuf = linelist[i].split()
                FracList.append(float(linebuf[0]))
                SFEDList.append(float(linebuf[1]))
            # Store the isf and esf values
            gamma_isf = SFEDList[size_0 + size_1 - 1]
            gamma_esf = SFEDList[size_0 + size_1 + size_2 - 1]

        # delete the output file
        os.system("rm " + stack_data_flnm)
        os.system("rm " + stack_inp_flnm)

        time_sf_coarse_end = time.perf_counter()

        # ------------------------------------------------------------------------------
        #             Refinement to locate the unstable position - gamma_us
        # ------------------------------------------------------------------------------
        # Locate the unstable stacking fault energy
        us_rough_Idx, us_rough_val = max(
            enumerate(SFEDList[0 : size_0 + size_1 - 1]), key=operator.itemgetter(1)
        )

        SFrac_us = FracList[us_rough_Idx - 1]
        dFrac_us = FracList[us_rough_Idx] - FracList[us_rough_Idx - 1]

        # Make input for the refinement
        with open(stack_inp_flnm, "w") as fstack:
            InpStr = setup_problem(
                Species,
                Model,
                N_Layers,
                LatConst,
                Pressure,
                Rigid_Grp_SIdx,
                Rigid_Grp_EIdx,
                N_Twin_Layers,
            )
            fstack.write(InpStr)
            InpStr = make_refine_us(SFrac_us, dFrac_us, stack_data_flnm)
            fstack.write(InpStr)

        # Run the LAMMPS script
        os.system(LAMMPS_command + " -in " + stack_inp_flnm + " -log " + stack_log_flnm)

        # Read the Lammps output file
        with open(stack_data_flnm) as fstack:
            linelist = fstack.readlines()
            linebuf = linelist[1].split()
            frac_us = float(linebuf[0])
            gamma_us = float(linebuf[1])

        # delete the output file
        os.system("rm " + stack_data_flnm)
        os.system("rm " + stack_inp_flnm)

        # ------------------------------------------------------------------------------
        #             Refinement to locate the unstable position - gamma_ut
        # ------------------------------------------------------------------------------
        # Locate the unstable stacking fault energy
        ut_rough_Idx, ut_rough_val = max(
            enumerate(SFEDList[size_0 + size_1 : size_0 + size_1 + size_2 - 1]),
            key=operator.itemgetter(1),
        )

        SFrac_ut = FracList[size_0 + size_1 + ut_rough_Idx - 1]
        dFrac_ut = (
            FracList[size_0 + size_1 + ut_rough_Idx]
            - FracList[size_0 + size_1 + ut_rough_Idx - 1]
        )

        # Make input for the refinement
        with open(stack_inp_flnm, "w") as fstack:
            InpStr = setup_problem(
                Species,
                Model,
                N_Layers,
                LatConst,
                Pressure,
                Rigid_Grp_SIdx,
                Rigid_Grp_EIdx,
                N_Twin_Layers,
            )
            fstack.write(InpStr)
            InpStr = make_refine_ut(SFrac_ut, dFrac_ut, stack_data_flnm)
            fstack.write(InpStr)

        # Run the LAMMPS script
        os.system(LAMMPS_command + " -in " + stack_inp_flnm + " -log " + stack_log_flnm)

        # Read the Lammps output file
        with open(stack_data_flnm) as fstack:
            linelist = fstack.readlines()
            linebuf = linelist[1].split()
            frac_ut = float(linebuf[0])
            gamma_ut = float(linebuf[1])

        # delete the output and log files
        os.system("rm " + stack_data_flnm)
        os.system("rm " + stack_inp_flnm)
        os.system("rm " + stack_log_flnm)
        if os.path.exists("kim.log"):
            os.system("rm kim.log")

        # # ------------------------------------------------------------------------------
        # #                    PRINT FINAL OUTPUTS TO KIM EDN FORMAT
        # # ------------------------------------------------------------------------------

        # Convert pressure to match relevant KIM Property Definitions
        CauchyStress = [-Pressure, -Pressure, -Pressure, 0.0, 0.0, 0.0]

        # ------------------------------------------------------------------------------
        #         Plot gamma surface to png and svg using matplotlib
        # ------------------------------------------------------------------------------
        # Convert data to numpy for matplotlib
        Gamma_X_dir1_frac, Gamma_Y_dir2_frac = (
            np.asarray(Gamma_X_dir1_frac),
            np.asarray(Gamma_Y_dir2_frac),
        )
        GammaSurf = np.array(GammaSurf)
        Gamma_X_dir1_frac_grid, Gamma_Y_dir2_frac_grid = np.meshgrid(
            Gamma_X_dir1_frac, Gamma_Y_dir2_frac
        )

        label112 = r"$\frac{s\,_{[112]}}{\sqrt{6}a/2}$"
        label110 = r"$\frac{s\,_{[\mathrm{\overline{1}}10]}}{\sqrt{2}a/2}$"
        energy_label = r"$\gamma$ (eV/$\mathrm{\AA}^2$)"
        labelfontsize = 15
        labelpadding3d = 20

        # Draw the 2d projection of the gamma surface
        plt.close("all")
        fig = plt.figure()

        ax_2d = fig.add_subplot()
        projected_gamma_surf = ax_2d.pcolor(
            Gamma_X_dir1_frac_grid, Gamma_Y_dir2_frac_grid, GammaSurf, cmap=cm.bone
        )
        ax_2d.set_xlabel(label112, fontsize=labelfontsize)
        ax_2d.set_ylabel(label110, fontsize=labelfontsize)
        fig.colorbar(projected_gamma_surf, shrink=1, aspect=10, label=energy_label)
        fig.subplots_adjust(bottom=0.1)
        fig.savefig(
            os.path.join(
                output_dir,
                "gamma-surface-relaxed-fcc-" + Species + "-" + Model + "-projected.png",
            ),
            bbox_inches="tight",
            dpi=300,
        )
        fig.savefig(
            os.path.join(
                output_dir,
                "gamma-surface-relaxed-fcc-" + Species + "-" + Model + "-projected.svg",
            ),
            bbox_inches="tight",
        )

        output_dict = {'CauchyStress': CauchyStress,
                       'Gamma_X_dir1_frac': Gamma_X_dir1_frac,
                       'Gamma_Y_dir2_frac': Gamma_Y_dir2_frac,
                       'GammaSurf': GammaSurf,
                       'gamma_us': gamma_us,
                       'gamma_isf': gamma_isf,
                       'gamma_ut': gamma_ut,
                       'gamma_esf': gamma_esf,
                       'frac_us': frac_us,
                       'frac_ut': frac_ut,
                       'FracList': FracList,
                       'SFEDList': SFEDList,
                       }
        
        time_gamma = time_gamma_end - time_gamma_start
        time_sf_coarse = time_sf_coarse_end - time_sf_coarse_start

        print(f"gamma surface time = {time_gamma/60} mins")
        print(f"time sf coarse = {time_sf_coarse/60} mins")
        return output_dict


# Function for printing to stderr
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
