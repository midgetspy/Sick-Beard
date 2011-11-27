#include <Python.h>
#include <exiv2/image.hpp>
#include <exiv2/exif.hpp>

PyObject *parse(PyObject *self, PyObject *args)
{
    char *fname;
    PyObject *ret = NULL, *entry = NULL, *keywords = NULL;
    unsigned char *data;
    Py_ssize_t len;

    if (!PyArg_ParseTuple(args, "s", &fname))
        return NULL;

    try {
	ret = PyDict_New();
	keywords = PyList_New(0);
	PyDict_SetItemString(ret, "Image.Keywords", keywords);

	Exiv2::Image::AutoPtr image = Exiv2::ImageFactory::open(fname);
	assert(image.get() != 0);
	image->readMetadata();

	entry = PyString_FromString(image->mimeType().c_str());
	PyDict_SetItemString(ret, "Image.Mimetype", entry);
	Py_DECREF(entry);

	entry = PyInt_FromLong(image->pixelWidth());
	PyDict_SetItemString(ret, "Image.Width", entry);
	Py_DECREF(entry);

	entry = PyInt_FromLong(image->pixelHeight());
	PyDict_SetItemString(ret, "Image.Height", entry);
	Py_DECREF(entry);

	Exiv2::ExifData &exifData = image->exifData();
	if (!exifData.empty()) {
	    Exiv2::ExifData::const_iterator end = exifData.end();
	    for (Exiv2::ExifData::const_iterator i = exifData.begin(); i != end; ++i) {
		if (!strcmp(i->typeName(), "Short") || !strcmp(i->typeName(), "Long"))
		    entry = PyInt_FromLong(i->value().toLong());
		else if ((!strcmp(i->typeName(), "Ascii")) || (!strcmp(i->typeName(), "Rational")))
		    entry = PyString_FromString(i->value().toString().c_str());
		else
		    entry = PyString_FromStringAndSize(i->value().toString().c_str(), i->count());
		PyDict_SetItemString(ret, i->key().c_str(), entry);
		Py_DECREF(entry);
	    }

	    Exiv2::ExifThumbC ExifThumb(exifData);
	    Exiv2::DataBuf databuf = ExifThumb.copy();
	    if (databuf.pData_) {
		entry = PyBuffer_New(databuf.size_);
		PyObject_AsWriteBuffer(entry, (void **)&data, &len);
		memcpy(data, databuf.pData_, databuf.size_);
		PyDict_SetItemString(ret, "Image.Thumbnail", entry);
		Py_DECREF(entry);
	    }
	}

	Exiv2::IptcData &iptcData = image->iptcData();
	if (!iptcData.empty()) {
	    Exiv2::IptcData::iterator end = iptcData.end();
	    for (Exiv2::IptcData::iterator i = iptcData.begin(); i != end; ++i) {
		if (i->key() == "Iptc.Application2.Keywords") {
		    entry = PyString_FromString(i->value().toString().c_str());
		    PyList_Append(keywords, entry);
		    Py_DECREF(entry);
		} else {
		    if (!strcmp(i->typeName(), "Short") || !strcmp(i->typeName(), "Long"))
			entry = PyInt_FromLong(i->value().toLong());
		    else if ((!strcmp(i->typeName(), "Ascii")) || (!strcmp(i->typeName(), "Rational")))
			entry = PyString_FromString(i->value().toString().c_str());
		    else
			entry = PyString_FromStringAndSize(i->value().toString().c_str(), i->count());
		    PyDict_SetItemString(ret, i->key().c_str(), entry);
		    Py_DECREF(entry);
		}
	    }
	}
	Py_DECREF(keywords);
	return ret;
    }

    catch (Exiv2::AnyError& e) {
	Py_DECREF(keywords);
	Py_DECREF(ret);
	PyErr_Format(PyExc_IOError, e.what());
	return NULL;
    }
}

PyMethodDef module_methods[] = {
    { "parse", parse, METH_VARARGS },
    { NULL }
};

extern "C"
void initexiv2() {
  Py_InitModule("exiv2", module_methods);
}
