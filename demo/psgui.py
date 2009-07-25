#!/usr/bin/env python

"""A minimal wx-based process manager."""

import os
import random

import wx
import psutil

ID_EXIT = 110


class MainGUIFrame(wx.Frame):
    """Main frame."""

    def __init__(self):
        wx.Frame.__init__(self, None, -1, "psutils", wx.Point(wx.CENTER_ON_SCREEN), (800, 600))
        self.SetMinSize((300,200))

        self.process_to_kill = ""

        self.current_pids = []
        self.pids_map = {}

        # Main panel
        panel = wx.Panel(self, -1)
        panel.SetBackgroundColour(wx.NamedColor('white'))

        # Process list
        self.process_list = wx.ListCtrl(panel, -1, style=wx.LC_REPORT|wx.NO_BORDER)

        self.process_list.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_right_click)

        self.process_list.InsertColumn(0, "Name")
        self.process_list.InsertColumn(1, "PID")
        self.process_list.InsertColumn(2, "PPID")
        self.process_list.InsertColumn(3, "Path")
        self.process_list.InsertColumn(4, "Command line")
        self.process_list.InsertColumn(5, "User")
        self.process_list.InsertColumn(6, "Group")
        self.process_list.InsertColumn(7, "CPU %")
        self.process_list.InsertColumn(8, "Mem %")

        self.process_list.SetColumnWidth(0, 120)  # name
        self.process_list.SetColumnWidth(1, 40)  # pid
        self.process_list.SetColumnWidth(2, 40)  # ppid
        self.process_list.SetColumnWidth(5, 100)  # user
        self.process_list.SetColumnWidth(6, 100)  # group
        self.process_list.SetColumnWidth(7, 50)  # cpu %
        self.process_list.SetColumnWidth(8, 50)  # mem %

        self.populate_list()

        # Panel sizer
        pso = wx.BoxSizer(wx.HORIZONTAL)
        pso.Add(self.process_list, 1, wx.EXPAND)

        psv = wx.BoxSizer(wx.VERTICAL)
        psv.Add(pso, 120, wx.EXPAND)

        panel.SetSizer(psv)

        # Menu bar
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        file_menu.AppendSeparator()
        file_menu.Append(ID_EXIT, "E&xit \tCtrl+X", "Close the application")

        menu_bar.Append(file_menu, "&File")

        # Binding menu bar entries with functions
        wx.EVT_MENU(self, ID_EXIT, self.on_exit_from_menu)

        # Setting the menu bar of the frame
        self.SetMenuBar(menu_bar)

        # Status bar
        self.status_bar = wx.StatusBar(self)

        self.states = ['','','0% CPU']
        self.status_bar.SetFields(self.states)
        self.SetStatusBar(self.status_bar)

        # Timers
        self.cpu_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.cpu_time, self.cpu_timer)
        self.cpu_timer.Start(1000)

        self.update_list_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_list, self.update_list_timer)
        self.update_list_timer.Start(1000)

    # Process handlers
    def populate_list(self):
        """Fill the list with info about processes"""
        new_pids = []
        removable_pids = []

        pids = psutil.get_pid_list()

        for pid in pids:
            if pid not in self.current_pids:
                new_pids.append(pid)

        for pid in self.current_pids:
            if pid not in pids:
                removable_pids.append(pid)

        while new_pids:
            pid = new_pids.pop(0)
            try:
                proc = psutil.Process(pid)
            except psutil.NoSuchProcess:
                # process disappeared on us
                continue
            try:
                cpu = round(proc.get_cpu_percent(), 1)
                mem = round(proc.get_memory_percent(), 1)

            except (psutil.AccessDenied, psutil.NoSuchProcess):
                cpu, mem = 'N/A', 'N/A'

            user = proc.username or 'N/A'
            if os.name == 'nt' and '\\' in user:
                user = user.split('\\')[1]

            row_id = self.process_list.Append((proc.name, proc.pid, proc.ppid,
                            proc.path, ' '.join(proc.cmdline), user, \
                            proc.groupname, cpu, mem))

            # display the row in green for 1 second
            self.process_list.SetItemBackgroundColour(row_id, wx.GREEN)

            def color_white(row_id):
                if row_id in self.pids_map.values():
                    self.process_list.SetItemBackgroundColour(row_id, wx.WHITE)

            wx.CallLater(1000, color_white, row_id)

            self.pids_map[pid] = row_id
            self.current_pids.append(pid)

        while removable_pids:
            pid = removable_pids.pop(0)
            row_id = self.pids_map[pid]

            # turn the row color in red for 1 second then remove the row
            self.process_list.SetItemBackgroundColour(row_id, wx.RED)
            wx.CallLater(1000, self.process_list.DeleteItem, row_id)

            self.current_pids.remove(pid)
            del self.pids_map[pid]

    def on_right_click(self, event):
        pid = int(self.process_list.GetItem(self.process_list.GetFirstSelected(),
                  1).GetText())

        menu = wx.Menu()
        id = wx.NewId()
        self.Bind(wx.EVT_MENU, lambda x: self.kill_process(pid), id=id)
        menu.Append(id, 'kill process')
        self.PopupMenu(menu)
        menu.Destroy()

    def kill_process(self, pid):
        if wx.MessageBox('Are you sure you want to kill this process?',
                         'WARNING', wx.ICON_EXCLAMATION|wx.YES_NO ) == wx.YES:
            psutil.Process(pid).kill()

    def cpu_time(self, event):
        """Handle the cpu usage timer's events"""
        self.states[2] = "%d%s CPU"%(psutil.cpu_percent(), "%")
        self.status_bar.SetFields(self.states)

    def update_list(self, event):
        """Call the function to update the list"""
        self.populate_list()

    # Menu bar handlers
    def on_exit_from_menu(self, event):
        """Close the frame"""
        self.Destroy()


class Application(wx.App):
    """wx application class. Hosts the event loop"""
    def OnInit(self):
        main = MainGUIFrame()
        main.Show()
        return True


if __name__ == '__main__':
    app = Application(redirect=False)
    app.MainLoop()
