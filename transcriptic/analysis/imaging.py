from transcriptic import ctx
from IPython.display import HTML
try:
    from StringIO import cStringIO as BytesIO
except ImportError:
    from io import BytesIO
from PIL import Image


class ImagePlate(object):
    '''
    An ImagePlate object generalizes the parsing of datasets derived from the
    plate camera for easy visualization.
    Parameters
    ----------
    dataset: dataset
        Single dataset selected from datasets object
    Attributes
    ----------
    raw: BytesIO
        Raw buffer of image bytes
    image: PIL.Image
        Image object as rendered by PIL
    '''

    def __init__(self, dataset):
        if ("image_normalized_loc" not in dataset.attributes or
                len(dataset.attributes["image_normalized_loc"]) == 0):
            raise RuntimeError("No data found in given dataset.")
        self.id = dataset.id
        self.raw = BytesIO()
        req = ctx.get("/-/%s.raw" % self.id, stream=True)
        # Buffer download of data
        chunk_sz = 512
        for chunk in req.iter_content(chunk_sz):
            self.raw.write(chunk)
        # Reset seek to 0
        self.raw.seek(0)
        self.image = Image.open(self.raw)

    def display(self):
        '''
        Displays the original full-sized image. Helpful when used in an IPython
        kernel
        Returns
        -------
        HTML
            Returns a HTML iframe of the full-size image which is rendered
            nicely in IPython
        '''
        return (HTML("""<iframe src="%s")" frameborder="0" \
                allowtransparency="true" style="height:500px;" seamless> \
                </iframe>""" % ctx.url("/-/%s.raw" % self.id)))
