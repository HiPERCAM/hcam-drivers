# Specific widgets, widget groups and parameters for hipercam instrument
from __future__ import print_function, unicode_literals, absolute_import, division
import tkinter as tk
from tkinter import filedialog, messagebox
import math
import json

# internal imports
from . import widgets as w
from . import get_root, DriverError
from .misc import (createJSON, saveJSON, postJSON,
                   execCommand, isRunActive)

# astropy
# from astropy import units as u

# Timing, Gain, Noise parameters
# TODO: insert real numbers here
VCLOCK = 14.4e-6  # vertical clocking time
HCLOCK = 0.48e-6  # horizontal clocking time
VIDEO_SLOW = 11.2e-6
VIDEO_MED = 6.24e-6
VIDEO_FAST = 3.2e-6
GAIN_FAST = 0.8  # electrons/ADU
GAIN_MED = 0.7
GAIN_SLOW = 0.8
RNO_FAST = 3.8  # e- / pixel
RNO_MED = 2.0
RNO_SLOW = 1.0
DARK_E = 0.001  # e/pix/s


FFX = 2048
FFY = 1024
IFY = 1024  # what is this?
IFX = 2048  # and this


class ExposureMultiplier(tk.LabelFrame):
    """
    Left to right group of RangedInt entry items to specify Nblue etc. Has a max
    number of columns after which it will jump to the left of next row and start over.
    """
    def __init__(self, master, labels, ivals, imins, imaxs,
                 ncmax, checker, blank, **kw):
        """
        Parameters
        ----------
        master : tk.widget
            enclosing widget
        labels : iterable
            labels for entry items
        ivals : list of int
            initial values
        imins : list of int
            minimum values
        imaxs : list of int
            maximum values
        ncmax : int
            maximum number of columns before wrapping
        checker : callable
            command that is run on any change to the entry
        blank : bool
            controls whether the field is allowed to be blank
            In some cases it makes things easier if blank fields are
            allowed, even if it is technically invalid
        kw : dict
            keyword arguments

        """
        super(ExposureMultiplier, self).__init__(master, bd=0)
        nitems = len(labels)
        if (len(ivals) != nitems or len(imins) != nitems or
                len(imaxs) != nitems):
            raise DriverError('ExposureMultiplier.__init__ values and options ' +
                              'must have same length')
        self.nitems = nitems
        self.labels = labels
        self.widgets = [w.RangedInt(self, ival, imin, imax, checker, blank, **kw) for
                        ival, imin, imax in zip(ivals, imins, imaxs)]
        row = 0
        col = 0
        for nw, widget in enumerate(self.widgets):
            tk.Label(self, text=labels[nw]).grid(row=row, column=col, sticky=tk.W)
            widget.grid(row=row+1, column=col, sticky=tk.W)
            col += 1
            if col == ncmax:
                row += 1
                col = 0

    def value(self, index):
        return self.widgets[index].value()

    def set(self, index, num):
        self.widgets[index].set(num)

    def getall(self):
        return [widget.value() for widget in self.widgets]

    def setall(self, nums):
        for index, val in enumerate(nums):
            self.set(index, val)

    def disable(self):
        for widget in self.widgets:
            widget.configure(state='disable')

    def enable(self):
        for widget in self.widgets:
            widget.configure(state='normal')


class InstPars(tk.LabelFrame):
    """
    Instrument parameters block.

    This widget block contains the meat of hdriver. Window settings, readout speed
    etc.
    """
    def __init__(self, master):
        """
        master : enclosing widget
        """
        super(InstPars, self).__init__(master)

        # left hand side
        lhs = tk.Frame(self)

        # Application (mode)
        tk.Label(lhs, text='Mode').grid(row=0, column=0, sticky=tk.W)
        self.app = w.Radio(lhs, ('Full', 'Wins', 'Drift'), 3, self.check,
                           ('FullFrame', 'Windows', 'Drift'))
        self.app.grid(row=0, column=1, sticky=tk.W)

        # Clear enabled
        self.clearLab = tk.Label(lhs, text='Clear')
        self.clearLab.grid(row=1, column=0, sticky=tk.W)
        self.clear = w.OnOff(lhs, False, self.check)
        self.clear.grid(row=1, column=1, sticky=tk.W)

        # Overscan enabled
        self.oscanLab = tk.Label(lhs, text='Overscan')
        self.oscanLab.grid(row=2, column=0, sticky=tk.W)
        self.oscan = w.OnOff(lhs, False, self.check)
        self.oscan.grid(row=2, column=1, sticky=tk.W)

        # led on (expert mode only)
        self.ledLab = tk.Label(lhs, text='LED setting')
        self.ledLab.grid(row=3, column=0, sticky=tk.W)
        self.led = w.RangedInt(lhs, 0, 0, 4095, None, False, width=7)
        self.led.grid(row=3, column=1, pady=2, sticky=tk.W)
        self.ledValue = self.led.value()

        # Readout speed
        tk.Label(lhs, text='Readout speed').grid(row=4, column=0, sticky=tk.W)
        self.readSpeed = w.Select(lhs, 2, ('Fast', 'Medium', 'Slow'), self.check)
        self.readSpeed.grid(row=4, column=1, pady=2, sticky=tk.W)

        # Exp delay
        tk.Label(lhs, text='Exposure delay (s)').grid(row=5, column=0,
                                                      sticky=tk.W)
        self.expose = w.Expose(lhs, 0.1, 0., 1677.7207,
                               self.check, width=7)
        self.expose.grid(row=5, column=1, pady=2, sticky=tk.W)

        # num exp
        tk.Label(lhs, text='Num. exposures  ').grid(row=6, column=0,  sticky=tk.W)
        self.number = w.PosInt(lhs, 1, None, False, width=7)
        self.number.grid(row=6, column=1, pady=2, sticky=tk.W)

        # nb, ng, nr etc
        labels = ('nb', 'ng', 'nr', 'ni', 'nz')
        ivals = (1, 1, 1, 1, 1)
        imins = (1, 1, 1, 1, 1)
        imaxs = (20, 20, 20, 20, 20)
        self.nmult = ExposureMultiplier(lhs, labels, ivals, imins, imaxs,
                                        5, self.check, False, width=4)
        self.nmult.grid(row=7, column=0, columnspan=2,
                        pady=2, sticky=tk.W)

        # right hand side: window parameters
        rhs = tk.Frame(self)

        # xstart - LH window of pair
        xsls = (1, 1, 1, 1)
        xslmins = (1, 1, 1, 1)
        xslmaxs = (1024, 1024, 1024, 1024)
        # xstart - RH window of pair
        xsrs = (1025, 1025, 1025, 1025)
        xsrmins = (1025, 1025, 1025, 1025)
        xsrmaxs = (2048, 2048, 2048, 2048)
        # ystart values
        yss = (1, 513, 1, 513)
        ysmins = (1, 513, 1, 513)
        ysmaxs = (512, 1024, 512, 1024)
        # sizes of windows (start at FF)
        nxs = (1024, 1024, 1024, 1024)
        nys = (512, 512, 512, 512)
        # allowed binning factors
        xbfac = (1, 2, 3, 4, 8)
        ybfac = (1, 2, 3, 4, 8)
        self.old_npair = 2
        self.wframe = w.WinPairs(rhs, xsls, xslmins, xslmaxs,
                                 xsrs, xsrmins, xsrmaxs,
                                 yss, ysmins, ysmaxs,
                                 nxs, nys, xbfac, ybfac,
                                 self.check)
        self.wframe.grid(row=2, column=0, columnspan=3,
                         sticky=tk.W+tk.N)

        # Pack two halfs
        lhs.pack(side=tk.LEFT, anchor=tk.N, padx=5)
        rhs.pack(side=tk.LEFT, anchor=tk.N, padx=5)

        # Store freeze state
        self.frozen = False

        self.setExpertLevel()

    def setExpertLevel(self):
        g = get_root(self).globals
        level = g.cpars['expert_level']
        if level == 0:
            self.ledLab.grid_forget()
            self.led.grid_forget()
            self.ledValue = self.led.value()
            self.led.set(0)
        else:
            self.led.set(self.ledValue)
            self.ledLab.grid(row=3, column=0, sticky=tk.W)
            self.led.grid(row=3, column=1, pady=2, sticky=tk.W)

    def isDrift(self):
        if self.app.value() == 'Drift':
            return True
        elif self.app.value() in ['FullFrame', 'Windows']:
            return False
        else:
            raise DriverError('InstPars.isDrift: application ' +
                              self.app.value() + ' not recognised')

    def isFF(self):
        if self.app.value() == 'FullFrame':
            return True
        elif self.app.value() in ['Drift', 'Windows']:
            return False
        else:
            raise DriverError('InstPars.isDrift: application ' +
                              self.app.value() + ' not recognised')

    def dumpJSON(self):
        """
        Encodes current parameters to JSON compatible dictionary
        """
        numexp = self.number.get()
        if numexp == 0:
            numexp = -1
        data = dict(
            numexp=self.number.value(),
            app=self.app.value(),
            led_flsh=self.led.value(),
            readout=self.readSpeed(),
            dwell=self.expose.value(),
            xbin=self.wframe.xbin.value(),
            ybin=self.wframe.ybin.value(),
            multipliers=self.nmult.getall(),
            clear=self.clear()
        )
        # add window mode
        if not self.isFF():
            for iw, (xsl, xsr, ys, nx, ny) in enumerate(self.wframe):
                data['x{}start_left'.format(iw+1)] = xsl
                data['x{}start_right'.format(iw+1)] = xsr
                data['y{}start'.format(iw+1)] = ys
                data['y{}size'.format(iw+1)] = ny
                data['x{}size'.format(iw+1)] = nx
        return data

    def loadJSON(self, json_string):
        """
        Loads in an application saved in JSON format.
        """
        data = json.loads(json_string)['appdata']
        # first set the parameters which change regardless of mode
        # number of exposures
        numexp = data.get('numexp', 0)
        if numexp == -1:
            numexp = 0
        self.number.set(numexp)
        # LED setting
        self.led.set(data.get('led_flsh', 0))
        # readout speed
        self.readSpeed.set(data.get('readout', 'Slow'))
        # dwell
        dwell = data.get('dwell', 0)
        self.expose.set(str(float(dwell)))
        # binning
        self.wframe.xbin.set(data.get('xbin', 1))
        self.wframe.ybin.set(data.get('ybin', 1))
        # multipliers
        mult_values = data.get('multipliers',
                               (1, 1, 1, 1, 1))
        self.nmult.setall(mult_values)

        # now for the behaviour which depends on mode
        if 'app' in data:
            self.app.set(data['app'])
            app = data['app']
            if app == 'Drift':
                # disable clear mode in drift
                self.clear.set(0)
                # only one pair allowed
                self.wframe.npair.set(1)

                # set the window pair values
                labels = ('x1start_left', 'y1_start',
                          'x1start_right', 'x1size',
                          'y1size')
                if not all(label in data for label in labels):
                    raise DriverError('Drift mode application missing window params')
                # now actually set them
                self.wframe.xsl[0].set(data['x1start_left'])
                self.wframe.xsr[0].set(data['x1start_right'])
                self.wframe.ys[0].set(data['y1_start'])
                self.wframe.nx[0].set(data['x1size'])
                self.wframe.ny[0].set(data['y1size'])

            elif app == 'FullFrame':
                # enable clear mode if set
                self.clear.set(data.get('clear', 0))

            elif app == 'Windows':
                # enable clear mode if set
                self.clear.set(data.get('clear', 0))
                nwin = 0
                for nw in range(4):
                    labels = ('x{0}start_left y{0}start ' +
                              'x{0}start_right x{0}size y{0}size').format(nw+1).split()
                    if all(label in data for label in labels):
                        xsl = data[labels[0]]
                        xsr = data[labels[2]]
                        ys = data[labels[1]]
                        nx = data[labels[3]]
                        ny = data[labels[4]]
                        self.wframe.xsl[nw].set(xsl)
                        self.wframe.xsr[nw].set(xsr)
                        self.wframe.ys[nw].set(ys)
                        self.wframe.nx[nw].set(nx)
                        self.wframe.ny[nw].set(ny)
                        nwin += 1
                    else:
                        break
                self.wframe.npair.set(nwin)

    def check(self, *args):
        """
        Callback to check validity of instrument parameters.

        Performs the following tasks:
            - spots and flags overlapping windows or null window parameters
            - flags windows with invalid dimensions given the binning parameter
            - sets the correct number of enabled windows
            - disables or enables clear button depending on drift mode or not
            - checks for window synchronisation, enabling sync button if required
            - enables or disables start button if settings are OK

        Returns
        -------
        status : bool
            True or False according to whether the settings are OK.
        """
        status = True
        if self.isDrift():
            self.clearLab.config(state='disable')
            if not self.frozen:
                self.clear.config(state='disable')
                self.old_npair = self.wframe.npair.value()
                self.wframe.npair.set(1)
                self.wframe.npair.allowed = (1,)
                self.wframe.enable()
                status = self.wframe.check()

        elif self.isFF():
            self.clearLab.config(state='normal')
            if not self.frozen:
                self.clear.config(state='normal')
                self.wframe.disable()

        else:
            self.clearLab.config(state='normal')
            if not self.frozen:
                self.clear.config(state='normal')
                self.wframe.npair.allowed = (2, 4)
                if self.wframe.npair.value() == 1:
                    self.wframe.npair.set(self.old_npair)
                self.wframe.enable()
                status = self.wframe.check()

        # exposure delay
        g = get_root(self).globals
        if self.expose.ok():
            self.expose.config(bg=g.COL['main'])
        else:
            self.expose.config(bg=g.COL['warn'])
            status = False

        # allow posting if parameters are OK. update count and SN estimates too
        if status:
            if (g.cpars['hcam_server_on'] and g.cpars['eso_server_online'] and
                    not isRunActive(g)):
                g.observe.start.enable()
            g.count.update()
        else:
            g.observe.start.disable()
        return status

    def freeze(self):
        """
        Freeze all settings so they cannot be altered
        """
        self.app.disable()
        self.clear.disable()
        self.led.disable()
        self.readSpeed.disable()
        self.expose.disable()
        self.number.disable()
        self.wframe.disable(everything=True)
        self.nmult.disable()
        self.frozen = True

    def unfreeze(self):
        """
        Reverse of freeze
        """
        self.app.enable()
        self.clear.enable()
        self.led.enable()
        self.readSpeed.enable()
        self.expose.enable()
        self.number.enable()
        self.wframe.enable()
        self.nmult.enable()
        self.frozen = False

    def getRtplotWins(self):
        """"
        Returns a string suitable to sending off to rtplot when
        it asks for window parameters. Returns null string '' if
        the windows are not OK. This operates on the basis of
        trying to send something back, even if it might not be
        OK as a window setup. Note that we have to take care
        here not to update any GUI components because this is
        called outside of the main thread.
        """
        try:
            if self.isFF():
                return ''
            else:
                xbin = self.wframe.xbin.value()
                ybin = self.wframe.ybin.value()
                nwin = 2*self.wframe.npair.value()
                ret = str(xbin) + ' ' + str(ybin) + ' ' + str(nwin) + '\r\n'
                for xsl, xsr, ys, nx, ny in self.wframe:
                    ret += '{:d} {:d} {:d} {:d}\r\n'.format(
                        xsl, ys, nx, ny
                    )
                    ret += '{:d} {:d} {:d} {:d}'.format(
                        xsr, ys, nx, ny
                    )
                return ret
        except:
            return ''

    def timing(self):
        """
        Estimates timing information for the current setup. You should
        run a check on the instrument parameters before calling this.

        Returns: (expTime, deadTime, cycleTime, dutyCycle)

        expTime   : exposure time per frame (seconds)
        deadTime  : dead time per frame (seconds)
        cycleTime : sampling time (cadence), (seconds)
        dutyCycle : percentage time exposing.
        frameRate : number of frames per second
        """
        # drift mode y/n?
        isDriftMode = self.isDrift()
        # FF y/n?
        isFF = self.isFF()

        # Set the readout speed
        readSpeed = self.readSpeed()

        if readSpeed == 'Fast':
            video = VIDEO_FAST
        elif readSpeed == 'Medium':
            video = VIDEO_MED
        elif readSpeed == 'Slow':
            video = VIDEO_SLOW
        else:
            raise DriverError('InstPars.timing: readout speed = ' +
                              readSpeed + ' not recognised.')

        # clear chip on/off?
        lclear = not isDriftMode and self.clear()

        # get exposure delay
        expose = self.expose.value()

        # window parameters
        xbin = self.wframe.xbin.value()
        ybin = self.wframe.ybin.value()
        if isDriftMode:
            # dxleft = self.wframe.xsl[0].value()
            # dxright = self.wframe.xsr[0].value()
            dys = self.wframe.ys[0].value()
            dnx = self.wframe.nx[0].value()
            dny = self.wframe.ny[0].value()
        elif isFF:
            nwin = 4
            xs = [1, 1024, 1, 1024]
            ys = [1, 513, 1, 513]
            nx = [1023, 1023, 1023, 1023]
            ny = [512, 512, 512, 512]
        else:
            xs, ys, nx, ny = [], [], [], []
            nwin = 2*self.wframe.npair.value()
            for xsl, xsr, ysv, nxv, nyv in self.wframe:
                xs.append(xsl)
                ys.append(ysv)
                nx.append(nxv)
                ny.append(nyv)
                xs.append(xsr)
                ys.append(ysv)
                nx.append(nxv)
                ny.append(nyv)

        # TODO: enable extra time for overscan

        # convert timing parameters to seconds
        expose_delay = expose

        # clear chip by VCLOCK-ing the image and storage areas
        if lclear:
            # accomodate changes to clearing made by DA to fix dark current
            # when clearing charge along normal output
            clear_time = 2.0*(FFY*VCLOCK+39.e-6) + FFX*HCLOCK
        else:
            clear_time = 0.0

        if isDriftMode:
            # for drift mode, we need the number of windows in the pipeline
            # and the pipeshift
            # TODO - correct for HiperCam
            pnwin = int(((1037 / dny) + 1)/2)
            pshift = 1037 - (2*pnwin-1)*dny
            frame_transfer = (dny+dys-1)*VCLOCK + 49.0e-6

            yshift = [0.]
            yshift[0] = (dys-1.0)*VCLOCK

            # After placing the window adjacent to the serial register, the
            # register must be cleared by clocking out the entire register,
            # taking FFX hclocks (we no longer open the dump gates, which
            # took only 8 hclock cycles to complete, but gave ramps and
            # bright rows in the bias).
            line_clear = [0.]
            if yshift[0] != 0:
                line_clear[0] = FFX*HCLOCK

            numhclocks = [0]
            numhclocks[0] = FFX

            line_read = [0.]
            line_read[0] = (VCLOCK*ybin + numhclocks[0]*HCLOCK +
                            video*2.0*dnx/xbin)

            readout = [0.]
            readout[0] = (dny/ybin) * line_read[0]

        else:
            # If not drift mode, move entire image into storage area
            # the -35 component is because Derek only shifts 1037 pixels
            # (composed of 1024 active rows, 5 dark reference rows, 2
            # transition rows and 6 extra overscan rows for good measure)
            # If drift mode, just move the window into the storage area
            frame_transfer = (FFY-35)*VCLOCK + 49.0e-6

            yshift = nwin*[0.]
            yshift[0] = (ys[0]-1.0)*VCLOCK
            for nw in range(1, nwin):
                yshift[nw] = (ys[nw]-ys[nw-1]-ny[nw-1])*VCLOCK

            line_clear = nwin*[0.]
            for nw in range(nwin):
                if yshift[nw] != 0:
                    line_clear[nw] = FFX*HCLOCK

            # calculate how long it takes to shift one row into the serial
            # register shift along serial register and then read out the data.
            # The charge in a row after a window used to be dumped, taking
            # 8 HCLOCK cycles. This created ramps and bright rows/columns in
            # the images, so was removed.
            numhclocks = nwin*[0]
            for nw in range(nwin):
                numhclocks[nw] = FFX

            line_read = nwin*[0.]
            for nw in range(nwin):
                line_read[nw] = (VCLOCK*ybin + numhclocks[nw]*HCLOCK +
                                 video*nx[nw]/xbin)

            # multiply time to shift one row into serial register by
            # number of rows for total readout time
            readout = nwin*[0.]
            for nw in range(nwin):
                readout[nw] = (ny[nw]/ybin) * line_read[nw]

        # now get the total time to read out one exposure.
        cycleTime = expose_delay + clear_time + frame_transfer
        if isDriftMode:
            cycleTime += pshift*VCLOCK+yshift[0]+line_clear[0]+readout[0]
        else:
            for nw in range(nwin):
                cycleTime += yshift[nw] + line_clear[nw] + readout[nw]

        frameRate = 1.0/cycleTime
        expTime = expose_delay if lclear else cycleTime - frame_transfer
        deadTime = cycleTime - expTime
        dutyCycle = 100.0*expTime/cycleTime

        return (expTime, deadTime, cycleTime, dutyCycle, frameRate)


class RunPars(tk.LabelFrame):
    """
    Run parameters
    """
    DTYPES = ('data', 'acquire', 'bias', 'flat', 'dark', 'tech')
    DVALS = ('data', 'data caution', 'bias', 'flat', 'dark', 'technical')

    def __init__(self, master):
        super(RunPars, self).__init__(master, text='Next run parameters',
                                      padx=10, pady=10)

        row = 0
        column = 0
        tk.Label(self, text='Target name').grid(row=row, column=column, sticky=tk.W)

        row += 1
        tk.Label(self, text='Filters').grid(row=row, column=column, sticky=tk.W)

        row += 1
        tk.Label(self, text='Programme ID').grid(row=row, column=column, sticky=tk.W)

        row += 1
        tk.Label(self, text='Principal Investigator').grid(row=row,
                                                           column=column, sticky=tk.W)

        row += 1
        tk.Label(self, text='Observer(s)').grid(row=row, column=column, sticky=tk.W)

        row += 1
        tk.Label(self, text='Pre-run comment').grid(row=row, column=column, sticky=tk.W)

        row += 1
        tk.Label(self, text='Data type').grid(row=row, column=column, sticky=tk.W+tk.N)

        # spacer
        column += 1
        tk.Label(self, text=' ').grid(row=0, column=column)

        # target
        row = 0
        column += 1
        self.target = w.Target(self, self.check)
        self.target.grid(row=row, column=column, sticky=tk.W)

        # filter
        row += 1
        self.filter = w.TextEntry(self, 20, self.check)
        self.filter.grid(row=row, column=column, sticky=tk.W)

        # programme ID
        row += 1
        self.progid = w.TextEntry(self, 20, self.check)
        self.progid.grid(row=row, column=column, sticky=tk.W)

        # principal investigator
        row += 1
        self.pi = w.TextEntry(self, 20, self.check)
        self.pi.grid(row=row, column=column, sticky=tk.W)

        # observers
        row += 1
        self.observers = w.TextEntry(self, 20, self.check)
        self.observers.grid(row=row, column=column, sticky=tk.W)

        # comment
        row += 1
        self.comment = w.TextEntry(self, 38)
        self.comment.grid(row=row, column=column, sticky=tk.W)

        # data type
        row += 1
        self.dtype = w.Radio(self, RunPars.DTYPES, 3, self.check,
                             values=RunPars.DVALS)
        self.dtype.set('UNDEF')
        self.dtype.grid(row=row, column=column, sticky=tk.W)

    def loadJSON(self, json_string):
        """
        Sets the values of the run parameters given an JSON string
        """
        user = json.loads(json_string)['user']

        def getUser(user, param):
            return user.get(param, '')

        self.target.set(getUser(user, 'target'))
        self.progid.set(getUser(user, 'ID'))
        self.pi.set(getUser(user, 'PI'))
        self.observers.set(getUser(user, 'Observers'))
        self.comment.set(getUser(user, 'comment'))
        self.dtype.set(getUser(user, 'flags'))
        self.filter.set(getUser(user, 'filters'))

    def dumpJSON(self):
        """
        Encodes current parameters to JSON compatible dictionary
        """
        return dict(
            target=self.target.value(),
            ID=self.progid.value(),
            PI=self.pi.value(),
            Observers=self.observers.value(),
            comment=self.comment.value(),
            flags=self.dtype.value(),
            filters=self.filter.value()
        )

    def check(self, *args):
        """
        Checks the validity of the run parameters. Returns
        flag (True = OK), and a message which indicates the
        nature of the problem if the flag is False.
        """

        ok = True
        msg = ''
        g = get_root(self).globals

        if self.dtype.value() == 'bias' or self.dtype.value() == 'flat' or \
           self.dtype.value() == 'dark':
            self.pi.configure(state='disable')
            self.progid.configure(state='disable')
            self.target.disable()
        else:
            self.pi.configure(state='normal')
            self.progid.configure(state='normal')
            self.target.enable()

        if g.cpars['require_run_params']:
            dtype = self.dtype.value()
            if dtype not in RunPars.DVALS:
                ok = False
                msg += 'No data type has been defined\n'

            if self.target.ok():
                self.target.entry.config(bg=g.COL['main'])
            else:
                self.target.entry.config(bg=g.COL['error'])
                ok = False
                msg += 'Target name field cannot be blank\n'

            if dtype == 'data caution' or \
               dtype == 'data' or dtype == 'technical':

                if self.progid.ok():
                    self.progid.config(bg=g.COL['main'])
                else:
                    self.progid.config(bg=g.COL['error'])
                    ok = False
                    msg += 'Programme ID field cannot be blank\n'

                if self.pi.ok():
                    self.pi.config(bg=g.COL['main'])
                else:
                    self.pi.config(bg=g.COL['error'])
                    ok = False
                    msg += 'Principal Investigator field cannot be blank\n'

            if self.observers.ok():
                self.observers.config(bg=g.COL['main'])
            else:
                self.observers.config(bg=g.COL['error'])
                ok = False
                msg += 'Observers field cannot be blank'
        return (ok, msg)

    def freeze(self):
        """
        Freeze all settings so that they can't be altered
        """
        self.target.disable()
        self.filter.configure(state='disable')
        self.progid.configure(state='disable')
        self.pi.configure(state='disable')
        self.observers.configure(state='disable')
        self.comment.configure(state='disable')
        self.dtype.disable()

    def unfreeze(self):
        """
        Unfreeze all settings so that they can be altered
        """
        self.filter.configure(state='normal')
        dtype = self.dtype.value()
        if dtype == 'data caution' or dtype == 'data' or dtype == 'technical':
            self.progid.configure(state='normal')
            self.pi.configure(state='normal')
            self.target.enable()
        self.observers.configure(state='normal')
        self.comment.configure(state='normal')
        self.dtype.enable()


class CountsFrame(tk.LabelFrame):
    """
    Frame for count rate estimates
    """
    def __init__(self, master):
        """
        master : enclosing widget
        """
        super(CountsFrame, self).__init__(master, pady=2,
                                          text='Count & S-to-N estimator')

        # divide into left and right frames
        lframe = tk.Frame(self, padx=2)
        rframe = tk.Frame(self, padx=2)

        # entries
        self.filter = w.Radio(lframe,
                              ('u', 'g', 'r', 'i', 'z'), 3,
                              self.checkUpdate, initial=1)
        self.mag = w.RangedFloat(lframe, 18., 0., 30.,
                                 self.checkUpdate, True, width=5)
        self.seeing = w.RangedFloat(lframe, 1.0, 0.2, 20.,
                                    self.checkUpdate, True, True,
                                    width=5)
        self.airmass = w.RangedFloat(lframe, 1.5, 1.0, 5.0,
                                     self.checkUpdate, True, width=5)
        self.moon = w.Radio(lframe, ('d', 'g', 'b'),  3, self.checkUpdate)

        # results
        self.cadence = w.Ilabel(rframe, text='UNDEF', width=10, anchor=tk.W)
        self.exposure = w.Ilabel(rframe, text='UNDEF', width=10, anchor=tk.W)
        self.duty = w.Ilabel(rframe, text='UNDEF', width=10, anchor=tk.W)
        self.peak = w.Ilabel(rframe, text='UNDEF', width=10, anchor=tk.W)
        self.total = w.Ilabel(rframe, text='UNDEF', width=10, anchor=tk.W)
        self.ston = w.Ilabel(rframe, text='UNDEF', width=10, anchor=tk.W)
        self.ston3 = w.Ilabel(rframe, text='UNDEF', width=10, anchor=tk.W)

        # layout
        # left
        tk.Label(lframe, text='Filter:').grid(row=0, column=0,
                                              padx=5, pady=3, sticky=tk.W+tk.N)
        self.filter.grid(row=0, column=1, padx=5, pady=3, sticky=tk.W)

        tk.Label(lframe, text='Mag:').grid(row=1, column=0, padx=5,
                                           pady=3, sticky=tk.W)
        self.mag.grid(row=1, column=1, padx=5, pady=3, sticky=tk.W)

        tk.Label(lframe, text='Seeing:').grid(row=2, column=0, padx=5,
                                              pady=3, sticky=tk.W)
        self.seeing.grid(row=2, column=1, padx=5, pady=3, sticky=tk.W)

        tk.Label(lframe, text='Airmass:').grid(row=3, column=0, padx=5,
                                               pady=3, sticky=tk.W)
        self.airmass.grid(row=3, column=1, padx=5, pady=3, sticky=tk.W)

        tk.Label(lframe, text='Moon:').grid(row=4, column=0, padx=5,
                                            pady=3, sticky=tk.W)
        self.moon.grid(row=4, column=1, padx=5, pady=3, sticky=tk.W)

        # right
        tk.Label(rframe, text='Cadence:').grid(row=0, column=0, padx=5,
                                               pady=3, sticky=tk.W)
        self.cadence.grid(row=0, column=1, padx=5, pady=3, sticky=tk.W)

        tk.Label(rframe, text='Exposure:').grid(row=1, column=0, padx=5,
                                                pady=3, sticky=tk.W)
        self.exposure.grid(row=1, column=1, padx=5, pady=3, sticky=tk.W)

        tk.Label(rframe, text='Duty cycle:').grid(row=2, column=0, padx=5,
                                                  pady=3, sticky=tk.W)
        self.duty.grid(row=2, column=1, padx=5, pady=3, sticky=tk.W)

        tk.Label(rframe, text='Peak:').grid(row=3, column=0, padx=5, pady=3,
                                            sticky=tk.W)
        self.peak.grid(row=3, column=1, padx=5, pady=3, sticky=tk.W)

        tk.Label(rframe, text='Total:').grid(row=4, column=0, padx=5,
                                             pady=3, sticky=tk.W)
        self.total.grid(row=4, column=1, padx=5, pady=3, sticky=tk.W)

        tk.Label(rframe, text='S/N:').grid(row=5, column=0, padx=5, pady=3, sticky=tk.W)
        self.ston.grid(row=5, column=1, padx=5, pady=3, sticky=tk.W)

        tk.Label(rframe, text='S/N (3h):').grid(row=6, column=0, padx=5,
                                                pady=3, sticky=tk.W)
        self.ston3.grid(row=6, column=1, padx=5, pady=3, sticky=tk.W)

        # slot frames in
        lframe.grid(row=0, column=0, sticky=tk.W+tk.N)
        rframe.grid(row=0, column=1, sticky=tk.W+tk.N)

    def checkUpdate(self, *args):
        """
        Updates values after first checking instrument parameters are OK.
        This is not integrated within update to prevent ifinite recursion
        since update gets called from ipars.
        """
        g = get_root(self).globals
        if not self.check():
            g.clog.warn('Current observing parameters are not valid.')
            return False

        if not g.ipars.check():
            g.clog.warn('Current instrument parameters are not valid.')
            return False

    def check(self):
        """
        Checks values
        """
        status = True
        g = get_root(self).globals
        if self.mag.ok():
            self.mag.config(bg=g.COL['main'])
        else:
            self.mag.config(bg=g.COL['warn'])
            status = False

        if self.airmass.ok():
            self.airmass.config(bg=g.COL['main'])
        else:
            self.airmass.config(bg=g.COL['warn'])
            status = False

        if self.seeing.ok():
            self.seeing.config(bg=g.COL['main'])
        else:
            self.seeing.config(bg=g.COL['warn'])
            status = False

        return status

    def update(self, *args):
        """
        Updates values. You should run a check on the instrument and
        target parameters before calling this.
        """
        g = get_root(self).globals
        expTime, deadTime, cycleTime, dutyCycle, frameRate = g.ipars.timing()

        total, peak, peakSat, peakWarn, ston, ston3 = \
            self.counts(expTime, cycleTime)

        if cycleTime < 0.01:
            self.cadence.config(text='{0:7.5f} s'.format(cycleTime))
        elif cycleTime < 0.1:
            self.cadence.config(text='{0:6.4f} s'.format(cycleTime))
        elif cycleTime < 1.:
            self.cadence.config(text='{0:5.3f} s'.format(cycleTime))
        elif cycleTime < 10.:
            self.cadence.config(text='{0:4.2f} s'.format(cycleTime))
        elif cycleTime < 100.:
            self.cadence.config(text='{0:4.1f} s'.format(cycleTime))
        elif cycleTime < 1000.:
            self.cadence.config(text='{0:4.0f} s'.format(cycleTime))
        else:
            self.cadence.config(text='{0:5.0f} s'.format(cycleTime))

        if expTime < 0.01:
            self.exposure.config(text='{0:7.5f} s'.format(expTime))
        elif expTime < 0.1:
            self.exposure.config(text='{0:6.4f} s'.format(expTime))
        elif expTime < 1.:
            self.exposure.config(text='{0:5.3f} s'.format(expTime))
        elif expTime < 10.:
            self.exposure.config(text='{0:4.2f} s'.format(expTime))
        elif expTime < 100.:
            self.exposure.config(text='{0:4.1f} s'.format(expTime))
        elif expTime < 1000.:
            self.exposure.config(text='{0:4.0f} s'.format(expTime))
        else:
            self.exposure.config(text='{0:5.0f} s'.format(expTime))

        self.duty.config(text='{0:4.1f} %'.format(dutyCycle))
        self.peak.config(text='{0:d} cts'.format(int(round(peak))))
        if peakSat:
            self.peak.config(bg=g.COL['error'])
        elif peakWarn:
            self.peak.config(bg=g.COL['warn'])
        else:
            self.peak.config(bg=g.COL['main'])

        self.total.config(text='{0:d} cts'.format(int(round(total))))
        self.ston.config(text='{0:.1f}'.format(ston))
        self.ston3.config(text='{0:.1f}'.format(ston3))

    def counts(self, expTime, cycleTime, ap_scale=1.6, ndiv=5):
        """
        Computes counts per pixel, total counts, sky counts
        etc given current magnitude, seeing etc. You should
        run a check on the instrument parameters before calling
        this.

        expTime   : exposure time per frame (seconds)
        cycleTime : sampling, cadence (seconds)
        ap_scale  : aperture radius as multiple of seeing

        Returns: (total, peak, peakSat, peakWarn, ston, ston3)

        total    -- total number of object counts in aperture
        peak     -- peak counts in a pixel
        peakSat  -- flag to indicate saturation
        peakWarn -- flag to indication level approaching saturation
        ston     -- signal-to-noise per exposure
        ston3    -- signal-to-noise after 3 hours on target
        """

        # code directly translated from Java equivalent.
        g = get_root(self).globals

        # Set the readout speed
        readSpeed = g.ipars.readSpeed()
        if readSpeed == 'Fast':
            gain = GAIN_FAST
            read = RNO_FAST
        elif readSpeed == 'Medium':
            gain = GAIN_MED
            read = RNO_MED
        elif readSpeed == 'Slow':
            gain = GAIN_SLOW
            read = RNO_SLOW
        else:
            raise DriverError('CountsFrame.counts: readout speed = ' +
                              readSpeed + ' not recognised.')

        xbin, ybin = g.ipars.wframe.xbin.value(), g.ipars.wframe.ybin.value()

        # calculate SN info.
        zero, sky, skyTot, darkTot = 0., 0., 0., 0.
        total, peak, correct, signal, readTot, seeing = 0., 0., 0., 0., 0., 0.
        noise,  skyPerPixel, narcsec, npix, signalToNoise3 = 1., 0., 0., 0., 0.

        tinfo = g.TINS[g.cpars['telins_name']]
        filtnam = self.filter.value()

        zero = tinfo['zerop'][filtnam]
        mag = self.mag.value()
        seeing = self.seeing.value()
        sky = g.SKY[self.moon.value()][filtnam]
        airmass = self.airmass.value()
        plateScale = tinfo['plateScale']

        # calculate expected electrons
        total = 10.**((zero-mag-airmass*g.EXTINCTION[filtnam])/2.5)*expTime

        # compute fraction that fall in central pixel
        # assuming target exactly at its centre. Do this
        # by splitting each pixel of the central (potentially
        # binned) pixel into ndiv * ndiv points at
        # which the seeing profile is added. sigma is the
        # RMS seeing in terms of pixels.
        sigma = seeing/g.EFAC/plateScale

        sum = 0.
        for iyp in range(ybin):
            yoff = -ybin/2.+iyp
            for ixp in range(xbin):
                xoff = -xbin/2.+ixp
                for iys in range(ndiv):
                    y = (yoff + (iys+0.5)/ndiv)/sigma
                    for ixs in range(ndiv):
                        x = (xoff + (ixs+0.5)/ndiv)/sigma
                        sum += math.exp(-(x*x+y*y)/2.)
        peak = total*sum/(2.*math.pi*sigma**2*ndiv**2)

        # Work out fraction of flux in aperture with radius AP_SCALE*seeing
        correct = 1. - math.exp(-(g.EFAC*ap_scale)**2/2.)

        # expected sky e- per arcsec
        skyPerArcsec = 10.**((zero-sky)/2.5)*expTime
        skyPerPixel = skyPerArcsec*plateScale**2*xbin*ybin
        narcsec = math.pi*(ap_scale*seeing)**2
        skyTot = skyPerArcsec*narcsec
        npix = math.pi*(ap_scale*seeing/plateScale)**2/xbin/ybin

        signal = correct*total  # in electrons
        darkTot = npix*DARK_E*expTime  # in electrons
        readTot = npix*read**2  # in electrons

        # noise, in electrons
        noise = math.sqrt(readTot + darkTot + skyTot + signal)

        # Now compute signal-to-noise in 3 hour seconds run
        signalToNoise3 = signal/noise*math.sqrt(3*3600./cycleTime)

        # convert from electrons to counts
        total /= gain
        peak /= gain

        warn = 25000
        sat = 60000

        peakSat = peak > sat
        peakWarn = peak > warn

        return (total, peak, peakSat, peakWarn, signal/noise, signalToNoise3)


class Start(w.ActButton):
    """
    Button to start a run.

    This is a complex process including the following steps:

    -- check the instrument and run parameters are OK
    -- optionally, hassle the user if the target changes
    -- optionally, pull in TCS info for the headers
    -- post the run settings to the ESO NGC control server
    -- start the run
    -- update the button status
    -- start the exposure timer

    TODO: complete optional tasks
    """
    def __init__(self, master, width):
        """
        Parameters
        ----------
        master : tk
            containing widget
        width : int
            width of button
        """
        super(Start, self).__init__(master, width, text='Start')
        g = get_root(self).globals
        self.config(bg=g.COL['start'])

        self.target = None

    def enable(self):
        """
        Enable the button
        """
        super(Start, self).enable()
        g = get_root(self).globals
        self.config(bg=g.COL['start'])

    def disable(self):
        """
        Disable the button, if in non-expert mode.
        """
        super(Start, self).disable()
        g = get_root(self).globals
        if self._expert:
            self.config(bg=g.COL['start'])
        else:
            self.config(bg=g.COL['startD'])

    def setExpert(self):
        """
        Turns on 'expert' status whereby the button is always enabled,
        regardless of its activity status.
        """
        super(Start, self).setExpert()
        g = get_root(self).globals
        self.config(bg=g.COL['start'])

    def setNonExpert(self):
        """
        Turns off 'expert' status whereby to allow a button to be disabled
        """
        self._expert = False
        if self._active:
            self.enable()
        else:
            self.disable()

    def act(self):
        """
        Carries out action associated with start button
        """
        if not messagebox.askokcancel('Confirm', 'Really start?'):
            return False

        # Check instrument pars are OK
        g = get_root(self).globals
        if not g.ipars.check():
            g.clog.warn('Invalid instrument parameters; save failed.')
            return False

        # create JSON to post
        data = createJSON(g)

        # POST
        success = postJSON(g, data)
        if not success:
            return False

        # START
        try:
            success = execCommand(g, 'start')
            if not success:
                raise Exception("Start command failed: check server response")
        except Exception as err:
            g.clog.warn('Failed to start run')
            g.clog.warn(str(err))
            return False

        # Run successfully started.
        # enable stop button, disable Start
        # start run timer
        self.disable()
        g.observe.stop.enable()
        g.info.timer.start()
        return True


class Load(w.ActButton):
    """
    Class defining the 'Load' button's operation. This loads a previously
    saved configuration from disk.
    """

    def __init__(self, master, width):
        """
        master  : containing widget
        width   : width of button
        """
        super(Load, self).__init__(master, width, text='Load')

    def act(self):
        """
        Carries out the action associated with the Load button
        """
        g = get_root(self).globals
        fname = filedialog.askopenfilename(
            defaultextension='.json', filetypes=[('json files', '.json'), ],
            initialdir=g.cpars['app_directory'])
        if not fname:
            g.clog.warn('Aborted load from disk')
            return False

        # load json
        with open(fname) as ifname:
            json_string = ifname.read()

        # load up the instrument settings
        g.ipars.loadJSON(json_string)

        # load up the run parameters
        g.rpars.loadJSON(json_string)

        return True


class Save(w.ActButton):
    """
    Class defining the 'Save' button's operation. This saves the
    current configuration to disk.
    """
    def __init__(self, master, width):
        """
        master  : containing widget
        width   : width of button
        """
        super(Save, self).__init__(master, width, text='Save')

    def act(self):
        """
        Carries out the action associated with the Save button
        """
        g = get_root(self).globals
        g.clog.info('\nSaving current application to disk')

        # check instrument parameters
        if not g.ipars.check():
            g.clog.warn('Invalid instrument parameters; save failed.')
            return False

        # check run parameters
        rok, msg = g.rpars.check()
        if not rok:
            g.clog.warn('Invalid run parameters; save failed.')
            g.clog.warn(msg)
            return False

        # Get data to save
        data = createJSON(g)

        # Save to disk
        if saveJSON(g, data):
            # modify buttons
            g.observe.load.enable()
            g.observe.unfreeze.disable()

            # unfreeze the instrument and run params
            g.ipars.unfreeze()
            g.rpars.unfreeze()
            return True
        else:
            return False


class Unfreeze(w.ActButton):
    """
    Class defining the 'Unfreeze' button's operation.
    """
    def __init__(self, master, width):
        """
        master  : containing widget
        width   : width of button
        """
        super(Unfreeze, self).__init__(master, width, text='Unfreeze')

    def act(self):
        """
        Carries out the action associated with the Unfreeze button
        """
        g = get_root(self).globals
        g.ipars.unfreeze()
        g.rpars.unfreeze()
        g.observe.load.enable()
        self.disable()


class Observe(tk.LabelFrame):
    """
    Observe widget. Collects together all the buttons needed for observing.
    """
    def __init__(self, master):
        super(Observe, self).__init__(master, padx=10, pady=10)

        width = 10
        self.load = Load(self, width)
        self.save = Save(self, width)
        self.unfreeze = Unfreeze(self, width)
        self.start = Start(self, width)
        self.stop = w.Stop(self, width)

        # Lay them out
        self.load.grid(row=0, column=0)
        self.save.grid(row=1, column=0)
        self.unfreeze.grid(row=2, column=0)
        self.start.grid(row=0, column=1)
        self.stop.grid(row=1, column=1)

        # Define initial status
        self.start.disable()
        self.stop.disable()
        self.unfreeze.disable()

        # Implement expert level
        self.setExpertLevel()

    def setExpertLevel(self):
        """
        Set expert level
        """
        g = get_root(self).globals
        level = g.cpars['expert_level']

        # now set whether buttons are permanently enabled or not
        if level == 0 or level == 1:
            self.load.setNonExpert()
            self.save.setNonExpert()
            self.unfreeze.setNonExpert()
            self.start.setNonExpert()
            self.stop.setNonExpert()

        elif level == 2:
            self.load.setExpert()
            self.save.setExpert()
            self.unfreeze.setExpert()
            self.start.setExpert()
            self.stop.setExpert()