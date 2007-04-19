
import itkExtras

# the viewer is a subclas of itk.pipeline, but not of a wx object
# The gui widgets is managed outside. It's made that way to avoid
# loading wx when importing itk module


class view( itkExtras.pipeline ):
  """A viewer to be used in the interpreter
  """
  
  def __init__(self, Input=None):
    import wx
    from vtk import vtkRenderer
    import itk
    
    # init the superclass
    itk.pipeline.__init__( self )
    
    self.frame = wx.Frame( None, -1, 'WrapITKViewer' )
    self.widget = WrapITKViewerWidget( self.frame )
    
    self.syncedViewers = []
    
    self.slice = [0, 0, 0]
    
    self.SetInput( Input )
    
  def GetSlice(self, dim):
    """Return the curent displayed sliceof the dimension dim.
    """
    return self.slice[dim]
  
  def SetSlice(self, dim, slice):
    """Set the current displayed slice on the dimension dim
    
    This method may have no visual effect in 2D mode, or if the orthoslice are
    disabled in 3D mode
    """
    self.slice[dim] = slice
  
  def GetCamera(self):
    """Return the camera currently used by the viewer
    """
    return self.widget.renderer.GetActiveCamera()
  
  def SetCamera(self, camera):
    """Set the camera to be used by the viewer
    """
    self.widget.renderer.SetActiveCamera( camera )
    
  def SetInput(self, Input):
    """Set the current input image
    """
    import itk
    img = itk.image( Input )
    
    if img :
      # Update to try to avoid to exit if a c++ exception is throwed
      # sadely, it will not prevent the program to exit later...
      # a real fix would be to wrap c++ exception in vtk
      img.UpdateOutputInformation()
      img.Update()
      
      # release the previous filters
      self.clear()
      
      itk.pipeline.SetInput( self, img )
      
      # flip the image to get the same representation than the vtk one
      self.connect( itk.FlipImageFilter[img].New() )
      axes = self[0].GetFlipAxes()
      axes.SetElement(1, True)
      self[0].SetFlipAxes(axes)
      
      # change the spacing while still keeping the ratio to workaround vtk bug
      # when spacing is very small
      spacing_ = itk.spacing(img)
      normSpacing = []
      for i in range(0, spacing_.Size()):
        normSpacing.append( spacing_.GetElement(i) / spacing_.GetElement(0) )
      self.connect( itk.ChangeInformationImageFilter[img].New( OutputSpacing=normSpacing, ChangeSpacing=True ) )
      
      # now really convert the data
      self.connect( itk.ImageToVTKImageFilter[img].New() )
      self.widget.SetInput( self[-1].GetImporter() )
    
    
#   def GetOverlay(self):
#     """Return the current overlay image
#     """
#     return self.overlay
#   
#   def SetOverlay(self, Overlay):
#     """Set the overlay image
#     """
#     self.overlay = Overlay
#     
  def GetColorTransferFuntion(self):
    """Return the color transfer function currently used
    """
    return self.colorAndOpacityEditor.GetColorTransferFuntion()
  
  def SetColorTransferFunction(self, func):
    """Set the color transfer function to use
    """
    self.colorAndOpacityEditor.SetColorTransferFuntion( func )
    
  def GetOpacityTransferFuntion(self):
    """Get the opacity transfer fucntion currently in use
    """
    self.colorAndOpacityEditor.GetOpacityTransferFuntion()
    
  def SetOpacityTransferFunction(self, func):
    """Set the opacity transfer function to be used
    """
    self.colorAndOpacityEditor.SetOpacityTransferFunction( func )
    
  def GetMode(self):
    """Return the current mode used by the viewer
    """
    return self.widget.mode.GetStringSelection()
  
  def SetMode(self, mode):
    """Set the viewer mode
    """
    if not self.widget.mode.SetStringSelection( mode ):
      raise ValueError("Invalid mode: "+str(mode))
    
  def Update( self ):
    self.widget.Update()
#     self.widget.Update()

  def SyncCamera( self, v ):
    v.SetCamera( self.GetCamera() )
    
    def sync1():
#       global renderInProgress
#       if not renderInProgress:
#         renderInProgress = True
#         try:
          v.widget.rendererWindow.Refresh()
#         except Exception, e:
#           renderInProgress = False
#           raise e
#         renderInProgress = False
        
    self.widget.renderer.AddObserver('EndEvent', sync1)
  
#     def sync2():
#       global renderInProgress
#       if not renderInProgress:
#         renderInProgress = True
#         try:
#           self.widget.rendererWindow.Refresh()
#         except Exception, e:
#           renderInProgress = False
#           raise e
#         renderInProgress = False
#   
#     v.widget.renderer.AddObserver('EndEvent', sync2)
  
  renderInProgress = False
    
  
import wx
import wx.lib.scrolledpanel
class WrapITKViewerWidget( wx.SplitterWindow ):
  def __init__(self, parent):
    wx.SplitterWindow.__init__(self, parent)
    
    #
    # setup the control panel
    #
    self.controlPanel = wx.lib.scrolledpanel.ScrolledPanel( self )
    
    vBox = wx.BoxSizer( wx.VERTICAL )
    
    self.mode = wx.RadioBox( self.controlPanel, label="Mode", choices=["2D", "3D"] )
    vBox.Add( self.mode, 0, wx.EXPAND )
    
    self.colorAndOpacityEditor = WrapITKColorAndOpacityEditor( self.controlPanel )
    vBox.Add( self.colorAndOpacityEditor, 0, wx.EXPAND )
    
    self.controlPanel.SetSizer( vBox )
    self.controlPanel.SetupScrolling()
    
    
    #
    # setup the render window
    #
    from vtk.wx.wxVTKRenderWindowInteractor import wxVTKRenderWindowInteractor
    from vtk import vtkRenderer, vtkVolumeTextureMapper2D, vtkVolumeProperty, vtkVolume
    self.rendererWindow = wxVTKRenderWindowInteractor(self, -1)
    self.renderer = vtkRenderer()
    self.rendererWindow.GetRenderWindow().AddRenderer(self.renderer)
    self.volumeMapper = vtkVolumeTextureMapper2D()
    self.volume = vtkVolume()
    self.volumeProperty = vtkVolumeProperty()
    self.volumeProperty.SetScalarOpacity( self.colorAndOpacityEditor.opacityTransferFunction )
    self.volumeProperty.SetColor( self.colorAndOpacityEditor.colorTransferFunction )
    self.volume.SetMapper( self.volumeMapper )
    self.volume.SetProperty( self.volumeProperty )
    self.renderer.AddVolume( self.volume )
    self.outline = None
    self.outlineMapper = None
    self.outlineActor = None
    
    # fill the split pane
    self.SplitVertically( self.controlPanel, self.rendererWindow )
    # avoid loosing on panel or the other
    self.SetMinimumPaneSize( 1 )
    
    # to manage update event correctly
    self.updateInProgress = False
    
    
  def SetInput( self, Input ):
    import vtk
    if "GetOutput" in dir(Input):
      self.inputFilter = Input
      self.inputFilter.AddObserver('EndEvent', self.Update)
      self.input = Input.GetOutput()
    else:
      self.inputFilter = None
      self.input = Input
      
    self.volumeMapper.SetInput( self.input )
    if not self.outline :
        self.outline = vtk.vtkOutlineFilter()
        self.outline.SetInput( self.input )
        self.outlineMapper = vtk.vtkPolyDataMapper()
        self.outlineMapper.SetInput( self.outline.GetOutput() )
        self.outlineActor = vtk.vtkActor()
        self.outlineActor.SetMapper( self.outlineMapper )
        self.renderer.AddActor( self.outlineActor )
    else :
        self.outline.SetInput( self.input )
        
    self.colorAndOpacityEditor.SetInput( self.input )

  def Update( self, *args ):
    if not self.updateInProgress :
      self.updateInProgress = True
      try:
        self.colorAndOpacityEditor.Update()
        self.rendererWindow.Render()
      except Exception, e:
        self.updateInProgress = False
        raise e
      self.updateInProgress = False
    
    
class WrapITKHistogram( wx.Panel ):
  def __init__( self, *args ):
    wx.Panel.__init__( self, *args )
    wx.EVT_PAINT(self, self.OnPaint)
    self.SetSize(wx.Size(100, 150))
    from vtk import vtkImageAccumulate
    self.accumulateFilter = vtkImageAccumulate()
    
  def OnPaint( self, event=None ):
    self.Draw( wx.PaintDC( self ) )
    
  def Draw( self, dc ):
    dc.Clear()
    # self.accumulateFilter.Update()
    histogram = self.accumulateFilter.GetOutput()
    minCount, maxCount = histogram.GetScalarRange()
    minValue, maxValue = self.accumulateFilter.GetInput().GetScalarRange()
    w, h = self.GetSize()
    
    for x in range( 0, self.GetSize()[0] ) :
      pixel = int( x / float( w ) * ( maxValue - minValue) + minValue )
      v = histogram.GetScalarComponentAsDouble(pixel, 0, 0, 0) / maxCount * h
      dc.SetPen( wx.Pen( "BLACK", 1 ) )
      dc.DrawLine( x, h-v, x, h )
      
  def SetInput( self, Input ):
    self.input = Input
    self.accumulateFilter.SetInput( self.input )
    self.Update()
    
  def Update( self ):
    self.input.Update()
    m, M = self.input.GetScalarRange()
    self.accumulateFilter.SetComponentExtent(m,M,0,0,0,0)
    self.accumulateFilter.Update()
    self.Draw( wx.ClientDC( self ) )
  
  
class WrapITKColorAndOpacityEditor( WrapITKHistogram ):
  def __init__( self, *args ):
    WrapITKHistogram.__init__( self, *args )
    from vtk import vtkPiecewiseFunction, vtkColorTransferFunction
    self.opacityTransferFunction = vtkPiecewiseFunction()
    self.colorTransferFunction = vtkColorTransferFunction()
    
    # add default values
    minVal, maxVal = 0, 255
    self.colorTransferFunction.AddHSVPoint(minVal, 0.0, 0.0, 0.0)
    self.colorTransferFunction.AddHSVPoint((maxVal-minVal)*0.25, 0.66, 1.0, 1.0)
    self.colorTransferFunction.AddHSVPoint((maxVal-minVal)*0.5,  0.44, 1.0, 1.0)
    self.colorTransferFunction.AddHSVPoint((maxVal-minVal)*0.75, 0.22, 1.0, 1.0)
    self.colorTransferFunction.AddHSVPoint(maxVal,               0.0,  1.0, 1.0)
    
    self.opacityTransferFunction.AddPoint(minVal, 0)
    self.opacityTransferFunction.AddPoint(maxVal, 1)
   

# sizer = wx.BoxSizer(wx.VERTICAL)
# sizer.Add(ww, 1, wx.EXPAND)
# frame.SetSizer(sizer)
# frame.Layout()
    