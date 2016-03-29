from OPSI.Object import *

class ObjectMethodsMixin(object):
	def test_getProductDependenciesFromBackend(self):
		productDependencies = self.backend.productDependency_getObjects()
		self.assertEqual(len(productDependencies),len(self.expected.productDependencies), u"Expected %s product dependencies, but got %s from backend." % (len(self.expected.productDependencies), len(productDependencies)))
		
	def test_updateProductDependencies(self):
		self.expected.productDependency2.requiredProductVersion = "2.0"
		self.expected.productDependency2.requirementType = None
		self.backend.productDependency_updateObject(self.expected.productDependency2)
		productDependencies = self.backend.productDependency_getObjects()
		
		self.assertEqual(len(productDependencies), len(self.expected.productDependencies), u"Expected %s product dependencies, but got %s from backend." % (len(self.expected.productDependencies), len(productDependencies)))
		for productDependency in productDependencies:
			if productDependency.getIdent() == self.expected.productDependency2.getIdent():
				self.assertEqual(productDependency.getRequiredProductVersion(), u"2.0", u"Expected required version to be %s but got %s." % (u"2.0", productDependency.getRequiredProductVersion()))
				self.assertEqual(productDependency.getRequirementType(),'before', u"Expected requirement type to be '%s' but got '%s.'" % ('before',productDependency.getRequirementType()))

	def test_deleteProductDependency(self):
		self.backend.productDependency_deleteObjects(self.expected.productDependency2)
		productDependencies = self.backend.productDependency_getObjects()
		self.assertEqual(len(productDependencies), len(self.expected.productDependencies) - 1, u"Expected %s product dependencies but got %s from backend." % (len(self.expected.productDependencies) - 1, len(productDependencies)))

	def test_createDuplicateProductDependency(self):
		self.backend.productDependency_createObjects(self.expected.productDependencies)
		productDependencies = self.backend.productDependency_getObjects()
		self.assertEqual(len(productDependencies), len(self.expected.productDependencies), u"Expected %s product dependencies but got %s from backend." % (len(self.expected.productDependencies), len(productDependencies)))
